import streamlit as st
import numpy as np
import requests
from datetime import datetime
# ---------------------------
# Image Quality Validation
# ---------------------------

from PIL import Image
import numpy as np

def validate_image_quality(uploaded_file):

    image = Image.open(uploaded_file)
    image_array = np.array(image)

    height, width = image_array.shape[:2]

    # Resolution check
    if width < 1500 or height < 1500:
        return False, "Image resolution too low (minimum 1500x1500 required)."

    # Convert to grayscale manually
    gray = np.mean(image_array, axis=2)

    # Blur detection using variance
    blur_score = np.var(gray)

    if blur_score < 300:
        return False, "Image appears too blurry."

    # Brightness check
    brightness = np.mean(gray)

    if brightness < 60:
        return False, "Image too dark."

    if brightness > 220:
        return False, "Image too bright / overexposed."

    return True, "Image passed quality checks."
# ---------------------------
# CONFIG
# ---------------------------

MODEL_VERSION = "v1.0-beta"

SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]

TABLE_URL = f"{SUPABASE_URL}/rest/v1/submissions"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# ---------------------------
# Invite Only
# ---------------------------

AUTHORIZED_USERS = [
    "Adaml"
]

user_email = st.text_input("Enter Access Email")

if user_email not in AUTHORIZED_USERS:
    st.warning("Invite-only beta. Access restricted.")
    st.stop()

# ---------------------------
# UI
# ---------------------------

st.set_page_config(page_title="Voodoo Sports Grading")

st.markdown("<h1 style='text-align:center;'>VOODOO SPORTS GRADING</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#C9A44D;'>PSA Pre-Screen Analyzer</p>", unsafe_allow_html=True)

st.divider()

front = st.file_uploader("Upload Front Image", type=["jpg", "png"])
back = st.file_uploader("Upload Back Image", type=["jpg", "png"])

st.divider()

manufacturer = st.text_input("Manufacturer")

stock_type = st.selectbox(
    "Stock Type",
    ["paper", "chrome", "refractor", "foil", "other"]
)

psa10 = st.number_input("PSA 10 Value", value=100.0)
psa9 = st.number_input("PSA 9 Value", value=50.0)
psa8 = st.number_input("PSA 8 Value", value=20.0)
fee = st.number_input("Grading Fee", value=25.0)

st.markdown("### Card Condition Inputs")

centering_input = st.slider("Centering (1-10)", 1, 10, 9)
corners_input = st.slider("Corners (1-10)", 1, 10, 9)
edges_input = st.slider("Edges (1-10)", 1, 10, 9)
surface_input = st.slider("Surface (1-10)", 1, 10, 9)

st.divider()

# ---------------------------
# Run Analysis
# ---------------------------

if st.button("Run Pre-Screen Analysis"):

    if not front or not back:
        st.error("Please upload BOTH front and back images.")

    else:

        # ---------------------------
        # Image Quality Validation
        # ---------------------------

        valid_front, message_front = validate_image_quality(front)
        if not valid_front:
            st.error(f"Front image issue: {message_front}")
            st.stop()

        valid_back, message_back = validate_image_quality(back)
        if not valid_back:
            st.error(f"Back image issue: {message_back}")
            st.stop()

        # ---------------------------
        # Weighted grading
        # ---------------------------

        weighted_grade = (
            centering_input * 0.35
            + corners_input * 0.25
            + edges_input * 0.20
            + surface_input * 0.20
        )

        mean = round(weighted_grade, 2)

        # Top-end compression
        if mean > 9:
        compression_factor = 0.4
        mean = 9 + (mean - 9) * compression_factor

        # Elite override rule (true 10 possible)
        if (
            centering_input == 10 and
            corners_input == 10 and
            edges_input == 10 and
            surface_input == 10 and
            component_variance == 0
        ):
    mean = 10

        # Grade ceiling logic
        lowest_component = min(
            centering_input,
            corners_input,
            edges_input,
            surface_input
        )

        if lowest_component <= 6:
            mean = min(mean, lowest_component + 1)

        if lowest_component <= 5:
            mean = min(mean, lowest_component + 0.5)

        # Confidence interval
        component_variance = np.var([
            centering_input,
            corners_input,
            edges_input,
            surface_input
        ])

        std = round(0.25 + component_variance * 0.1, 2)

        # Probability model
        def normal_pdf(x, mu, sigma):
            return np.exp(-0.5 * ((x - mu) / sigma) ** 2)

        sigma = max(std, 0.25)

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
            "submitted_by": user_email,
            "created_at": str(datetime.now())
        }

        response = requests.post(TABLE_URL, json=data, headers=headers)

        if response.status_code == 201:
            st.success("Submission saved to database.")
        else:
            st.error(f"Database error: {response.text}")
