import streamlit as st
import numpy as np
import requests
from datetime import datetime
import pandas as pd
import uuid

# ===============================
# BRAND STYLE
# ===============================

st.markdown("""
<style>
body {
    background: linear-gradient(135deg, #4B1E78 0%, #3A1460 100%);
    color: white;
}

.main {
    background: linear-gradient(135deg, #4B1E78 0%, #3A1460 100%);
}

h1, h2, h3 {
    color: #C9A44D;
}

hr {
    border: 1px solid rgba(255,255,255,0.15);
}

.stButton>button {
    background-color: #C9A44D;
    color: black;
    font-weight: bold;
    border-radius: 10px;
    padding: 0.7em 1.4em;
    border: none;
}

.section-box {
    background-color: rgba(0,0,0,0.25);
    padding: 20px;
    border-radius: 14px;
    margin-bottom: 18px;
    backdrop-filter: blur(6px);
}

.grade-box {
    background: linear-gradient(135deg, #C9A44D 0%, #E5C97A 100%);
    padding: 28px;
    border-radius: 18px;
    text-align: center;
    font-size: 48px;
    font-weight: bold;
    color: black;
    margin-bottom: 20px;
}

.stProgress > div > div > div {
    background-color: #C9A44D;
}
</style>
""", unsafe_allow_html=True)

# ===============================
# CONFIG
# ===============================

MODEL_VERSION = "v1.9-beta"

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

AUTHORIZED_USERS = ["Adaml"]

# ===============================
# ACCESS CONTROL
# ===============================

user_email = st.text_input("Enter Access Email")

if user_email not in AUTHORIZED_USERS:
    st.warning("Invite-only beta. Access restricted.")
    st.stop()

# ===============================
# HEADER
# ===============================

st.set_page_config(page_title="Voodoo Sports Grading")

st.image("logo.png", width=800)
st.markdown("<hr>", unsafe_allow_html=True)

# ===============================
# IMAGE UPLOAD
# ===============================

col1, col2 = st.columns(2)

with col1:
    front = st.file_uploader("Upload Front Image", type=["jpg", "png"])

with col2:
    back = st.file_uploader("Upload Back Image", type=["jpg", "png"])

# ===============================
# CARD INFO
# ===============================

st.markdown("<div class='section-box'>", unsafe_allow_html=True)

manufacturer = st.text_input("Manufacturer")
stock_type = st.selectbox("Stock Type", ["paper", "chrome", "refractor", "foil", "other"])

psa_is_graded = st.checkbox("Is this card already PSA graded?")
psa_actual_grade = (
    st.number_input("Enter PSA Actual Grade", min_value=1.0, max_value=10.0, step=0.5)
    if psa_is_graded else None
)

st.markdown("</div>", unsafe_allow_html=True)

# ===============================
# CONDITION INPUTS
# ===============================

st.markdown("<div class='section-box'>", unsafe_allow_html=True)

corners_input = st.slider("Corners (1-10)", 1, 10, 9)
edges_input = st.slider("Edges (1-10)", 1, 10, 9)
surface_input = st.slider("Surface (1-10)", 1, 10, 9)

st.markdown("</div>", unsafe_allow_html=True)

# ===============================
# RUN ANALYSIS
# ===============================

if st.button("Run Pre-Screen Analysis"):

    if not front or not back:
        st.error("Upload both images.")
        st.stop()

    # -------- Centering API --------
    response = requests.post(
        CENTERING_API_URL,
        files={"file": front.getvalue()}
    )

    if response.status_code != 200:
        st.error("Centering API failed.")
        st.stop()

    centering_result = response.json()

    if "error" in centering_result:
        raw_centering_score = 5.0
    else:
        h_ratio = float(centering_result["horizontal_ratio"])
        v_ratio = float(centering_result["vertical_ratio"])
        combined_ratio = (h_ratio + v_ratio) / 2
        raw_centering_score = round(combined_ratio * 10, 2)

    # Slab stabilization
    if psa_is_graded:
        auto_centering_score = 8.8
    else:
        auto_centering_score = raw_centering_score

    # -------- Grading --------
    weighted_grade = (
        auto_centering_score * 0.35
        + corners_input * 0.25
        + edges_input * 0.20
        + surface_input * 0.20
    )

    mean = round(weighted_grade, 2)

    if mean > 9:
        mean = 9 + (mean - 9) * 0.6

    if (
        auto_centering_score >= 8.8 and
        corners_input >= 9.5 and
        edges_input >= 9.5 and
        surface_input >= 9.5 and
        mean >= 9.3
    ):
        mean = 10.0

    # -------- Probability --------
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

    # ===============================
    # DISPLAY RESULTS
    # ===============================

    st.markdown(f"<div class='grade-box'>{mean}</div>", unsafe_allow_html=True)

    st.subheader("Grade Probability")

    st.progress(float(prob10))
    st.write(f"PSA 10: {round(prob10 * 100, 1)}%")

    st.progress(float(prob9))
    st.write(f"PSA 9: {round(prob9 * 100, 1)}%")

    st.progress(float(prob8))
    st.write(f"PSA ≤8: {round(prob8 * 100, 1)}%")

    # ===============================
    # SAVE TO SUPABASE
    # ===============================

    unique_id = str(uuid.uuid4())

    front_filename = f"{unique_id}_front.jpg"
    back_filename = f"{unique_id}_back.jpg"

    requests.post(
        f"{STORAGE_URL}/card-images/{front_filename}",
        headers={"Authorization": f"Bearer {SUPABASE_KEY}"},
        data=front.getvalue()
    )

    requests.post(
        f"{STORAGE_URL}/card-images/{back_filename}",
        headers={"Authorization": f"Bearer {SUPABASE_KEY}"},
        data=back.getvalue()
    )

    front_url = f"{SUPABASE_URL}/storage/v1/object/public/card-images/{front_filename}"
    back_url = f"{SUPABASE_URL}/storage/v1/object/public/card-images/{back_filename}"

    data = {
        "manufacturer": manufacturer,
        "stock_type": stock_type,
        "predicted_grade": mean,
        "prob_10": float(prob10),
        "prob_9": float(prob9),
        "prob_8_or_lower": float(prob8),
        "model_version": MODEL_VERSION,
        "submitted_by": user_email,
        "auto_centering_score": auto_centering_score,
        "raw_centering_score": raw_centering_score,
        "psa_is_graded": psa_is_graded,
        "psa_actual_grade": psa_actual_grade,
        "front_image_url": front_url,
        "back_image_url": back_url,
        "created_at": str(datetime.now())
    }

    save_response = requests.post(TABLE_URL, json=data, headers=headers)

    if save_response.status_code == 201:
        st.success("Submission saved.")
    else:
        st.error(f"Database error: {save_response.text}")

    with st.expander("Technical Details"):
        st.write("Raw Centering Score:", raw_centering_score)
        st.write("Centering Used:", auto_centering_score)
        st.write("Corners:", corners_input)
        st.write("Edges:", edges_input)
        st.write("Surface:", surface_input)

# ===============================
# ADMIN DASHBOARD
# ===============================

if user_email == "Adaml":

    st.markdown("<hr>", unsafe_allow_html=True)
    st.header("Calibration Dashboard")

    analytics_response = requests.get(TABLE_URL, headers=headers)

    if analytics_response.status_code == 200:
        df = pd.DataFrame(analytics_response.json())

        if len(df) > 0:

            if "psa_actual_grade" in df.columns:
                df_with_actual = df.dropna(subset=["psa_actual_grade"])

                if len(df_with_actual) > 0:
                    df_with_actual["prediction_error"] = (
                        df_with_actual["predicted_grade"]
                        - df_with_actual["psa_actual_grade"]
                    )

                    st.subheader("Prediction Accuracy")
                    st.write("MAE:",
                             round(abs(df_with_actual["prediction_error"]).mean(), 2))
                    st.write("Bias:",
                             round(df_with_actual["prediction_error"].mean(), 2))

            st.subheader("Grade Distribution")
            st.bar_chart(df["predicted_grade"].value_counts().sort_index())

            st.subheader("Raw Data")
            st.dataframe(df)
