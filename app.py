import streamlit as st
import numpy as np
import requests
from datetime import datetime
from PIL import Image
import uuid
import pandas as pd

# ===============================
# CONFIG
# ===============================

MODEL_VERSION = "v1.5-beta"

SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
CENTERING_API_URL = "https://voodoo-centering-api.onrender.com/analyze"

TABLE_URL = f"{SUPABASE_URL}/rest/v1/submissions"
STORAGE_URL = f"{SUPABASE_URL}/storage/v1/object"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# ===============================
# ACCESS CONTROL
# ===============================

AUTHORIZED_USERS = ["Adaml"]

user_email = st.text_input("Enter Access Email")

if user_email not in AUTHORIZED_USERS:
    st.warning("Invite-only beta. Access restricted.")
    st.stop()

# ===============================
# UI
# ===============================

st.set_page_config(page_title="Voodoo Sports Grading")
st.title("VOODOO SPORTS GRADING")
st.subheader("PSA Pre-Screen Analyzer")

front = st.file_uploader("Upload Front Image", type=["jpg", "png"])
back = st.file_uploader("Upload Back Image", type=["jpg", "png"])

manufacturer = st.text_input("Manufacturer")
stock_type = st.selectbox("Stock Type", ["paper", "chrome", "refractor", "foil", "other"])

psa10 = st.number_input("PSA 10 Value", value=100.0)
psa9 = st.number_input("PSA 9 Value", value=50.0)
psa8 = st.number_input("PSA 8 Value", value=20.0)
fee = st.number_input("Grading Fee", value=25.0)

psa_is_graded = st.checkbox("Is this card already PSA graded?")
psa_actual_grade = (
    st.number_input("Enter PSA Actual Grade", min_value=1.0, max_value=10.0, step=0.5)
    if psa_is_graded else None
)

corners_input = st.slider("Corners (1-10)", 1, 10, 9)
edges_input = st.slider("Edges (1-10)", 1, 10, 9)
surface_input = st.slider("Surface (1-10)", 1, 10, 9)

# ===============================
# RUN ANALYSIS
# ===============================

if st.button("Run Pre-Screen Analysis"):

    if not front or not back:
        st.error("Upload both images.")
        st.stop()

    # -----------------------------
    # Call Centering API
    # -----------------------------

    files = {"file": front.getvalue()}
    response = requests.post(CENTERING_API_URL, files={"file": front})

    if response.status_code != 200:
        st.error("Centering API failed.")
        st.stop()

    centering_result = response.json()

    if "error" in centering_result:
        auto_centering_score = 5.0  # neutral fallback
    else:
        h_ratio = centering_result["horizontal_ratio"]
        v_ratio = centering_result["vertical_ratio"]
        auto_centering_score = round(min(h_ratio, v_ratio) * 10, 2)

    # -----------------------------
    # Grading Logic
    # -----------------------------

    weighted_grade = (
        auto_centering_score * 0.35
        + corners_input * 0.25
        + edges_input * 0.20
        + surface_input * 0.20
    )

    mean = round(weighted_grade, 2)

    if mean > 9:
        mean = 9 + (mean - 9) * 0.4

    # Probability
    def normal_pdf(x, mu, sigma):
        return np.exp(-0.5 * ((x - mu) / sigma) ** 2)

    sigma = 0.3

    prob10 = normal_pdf(mean, 10, sigma)
    prob9 = normal_pdf(mean, 9, sigma)
    prob8 = normal_pdf(mean, 8, sigma)

    total = prob10 + prob9 + prob8
    prob10 /= total
    prob9 /= total
    prob8 /= total

    ev = (
        prob10 * psa10
        + prob9 * psa9
        + prob8 * psa8
    ) - fee

    # -----------------------------
    # Display
    # -----------------------------

    st.subheader("Pre-Screen Report")
    st.write("Auto Centering Score:", auto_centering_score)
    st.write("Final Predicted Grade:", round(mean, 2))

    st.write("PSA 10 Probability:", round(prob10 * 100, 1), "%")
    st.write("PSA 9 Probability:", round(prob9 * 100, 1), "%")
    st.write("PSA ≤8 Probability:", round(prob8 * 100, 1), "%")

    if ev > 0:
        st.success(f"Projected Profit: +${round(ev, 2)}")
    else:
        st.error(f"Projected Loss: -${abs(round(ev, 2))}")
