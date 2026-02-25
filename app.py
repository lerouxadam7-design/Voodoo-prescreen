import streamlit as st
import numpy as np
import requests
from datetime import datetime

MODEL_VERSION = "v1.0-beta"
# ---------------------------
# Invite-Only Access Control
# ---------------------------

AUTHORIZED_USERS = [
    "adaml",
    "trustedtester@email.com"
]

user_email = st.text_input("Enter Access Email")

if user_email not in AUTHORIZED_USERS:
    st.warning("Invite-only beta. Access restricted.")
    st.stop()
st.set_page_config(page_title="Voodoo Sports Grading")

# ---------------------------
# Supabase REST Setup
# ---------------------------
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]

TABLE_URL = f"{SUPABASE_URL}/rest/v1/submissions"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# ---------------------------
# Branding
# ---------------------------
st.markdown(
    "<h1 style='text-align:center;'>VOODOO SPORTS GRADING</h1>",
    unsafe_allow_html=True
)
st.markdown(
    "<p style='text-align:center; color:#C9A44D;'>PSA Pre-Screen Analyzer</p>",
    unsafe_allow_html=True
)

st.divider()

# ---------------------------
# Upload Section
# ---------------------------
front = st.file_uploader("Upload Front Image", type=["jpg", "png"])
back = st.file_uploader("Upload Back Image", type=["jpg", "png"])

st.divider()

# ---------------------------
# Card Inputs
# ---------------------------
manufacturer = st.text_input("Manufacturer")
stock_type = st.selectbox(
    "Stock Type",
    ["paper", "chrome", "refractor", "foil", "other"]
)

psa10 = st.number_input("PSA 10 Value", value=100.0)
psa9 = st.number_input("PSA 9 Value", value=50.0)
psa8 = st.number_input("PSA 8 Value", value=20.0)
fee = st.number_input("Grading Fee", value=25.0)

st.divider()
st.markdown("### Card Condition Inputs")

centering_input = st.slider("Centering (1-10)", 1, 10, 9)
corners_input = st.slider("Corners (1-10)", 1, 10, 9)
edges_input = st.slider("Edges (1-10)", 1, 10, 9)
surface_input = st.slider("Surface (1-10)", 1, 10, 9)
if st.button("Run Pre-Screen Analysis"):
if st.button("Run Pre-Screen Analysis"):

    if not front or not back:
        st.error("Please upload BOTH front and back images.")
    else:

        weighted_grade = (
            centering_input * 0.35
            + corners_input * 0.25
            + edges_input * 0.20
            + surface_input * 0.20
        )

        mean = round(weighted_grade, 2)

        component_variance = np.var([
            centering_input,
            corners_input,
            edges_input,
            surface_input
        ])

        std = round(0.25 + component_variance * 0.1, 2)

        prob10 = max(0, min(1, 1 - abs(mean - 10)))
        prob9 = max(0, min(1, 1 - abs(mean - 9)))
        prob8 = max(0, 1 - (prob10 + prob9))

        ev = (
            prob10 * psa10
            + prob9 * psa9
            + prob8 * psa8
        ) - fee

        st.subheader("Pre-Screen Report")

        st.markdown(
            f"<h2 style='color:#C9A44D;'>{mean}</h2>",
            unsafe_allow_html=True
        )

        st.write(f"Confidence Interval ±{std}")

        st.write("### Grade Probability")
        st.progress(prob10)
        st.write(f"PSA 10: {round(prob10*100,1)}%")

        st.progress(prob9)
        st.write(f"PSA 9: {round(prob9*100,1)}%")

        st.progress(prob8)
        st.write(f"PSA ≤8: {round(prob8*100,1)}%")

        if ev > 0:
            st.success(f"Projected Profit: +${round(ev,2)}")
        else:
            st.error(f"Projected Loss: -${abs(round(ev,2))}")

        data = {
            "manufacturer": manufacturer,
            "stock_type": stock_type,
            "psa10_value": psa10,
            "psa9_value": psa9,
            "psa8_value": psa8,
            "grading_fee": fee,
            "predicted_grade": mean,
            "prob_10": prob10,
            "prob_9": prob9,
            "prob_8_or_lower": prob8,
            "expected_value": ev,
            "confidence_interval": std,
            "model_version": MODEL_VERSION,
            "submitted_by": user_email
        }

        response = requests.post(TABLE_URL, json=data, headers=headers)

        if response.status_code == 201:
            st.success("Submission saved to database.")
        else:
            st.error(f"Database error: {response.text}")
