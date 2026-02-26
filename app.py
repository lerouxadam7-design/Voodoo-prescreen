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

MODEL_VERSION = "v1.3-beta"

SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]

TABLE_URL = f"{SUPABASE_URL}/rest/v1/submissions"
STORAGE_URL = f"{SUPABASE_URL}/storage/v1/object"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# ===============================
# INVITE ONLY ACCESS
# ===============================

AUTHORIZED_USERS = [
    "Adaml"
]

user_email = st.text_input("Enter Access Email")

if user_email not in AUTHORIZED_USERS:
    st.warning("Invite-only beta. Access restricted.")
    st.stop()

# ===============================
# IMAGE VALIDATION
# ===============================

def validate_image_quality(uploaded_file):

    image = Image.open(uploaded_file)
    image_array = np.array(image)

    height, width = image_array.shape[:2]

    if width < 1500 or height < 1500:
        return False, "Image resolution too low.", 0

    gray = np.mean(image_array, axis=2)

    blur_score = np.var(gray)
    brightness = np.mean(gray)

    quality_score = 100

    if blur_score < 300:
        quality_score -= 30

    if brightness < 60 or brightness > 220:
        quality_score -= 20

    return True, "Image passed quality checks.", quality_score

# ===============================
# AUTO CENTERING
# ===============================

def estimate_centering(uploaded_file):

    image = Image.open(uploaded_file)
    image_array = np.array(image)

    gray = np.mean(image_array, axis=2)

    col_gradient = np.abs(np.diff(np.mean(gray, axis=0)))
    row_gradient = np.abs(np.diff(np.mean(gray, axis=1)))

    left_border = np.argmax(col_gradient[:len(col_gradient)//2])
    right_border = len(col_gradient) - np.argmax(col_gradient[::-1][:len(col_gradient)//2])

    top_border = np.argmax(row_gradient[:len(row_gradient)//2])
    bottom_border = len(row_gradient) - np.argmax(row_gradient[::-1][:len(row_gradient)//2])

    card_width = right_border - left_border
    card_height = bottom_border - top_border

    if card_width <= 0 or card_height <= 0:
        return 0.0

    left_margin = left_border
    right_margin = len(gray[0]) - right_border
    top_margin = top_border
    bottom_margin = len(gray) - bottom_border

    horizontal_balance = min(left_margin, right_margin) / max(left_margin, right_margin)
    vertical_balance = min(top_margin, bottom_margin) / max(top_margin, bottom_margin)

    balance_ratio = min(horizontal_balance, vertical_balance)

    score = round(balance_ratio * 10, 2)

    return score

# ===============================
# UI
# ===============================

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

st.markdown("### PSA Status")

psa_is_graded = st.checkbox("Is this card already PSA graded?")

psa_actual_grade = None
if psa_is_graded:
    psa_actual_grade = st.number_input(
        "Enter PSA Actual Grade",
        min_value=1.0,
        max_value=10.0,
        step=0.5
    )

st.markdown("### Other Condition Inputs")

corners_input = st.slider("Corners (1-10)", 1, 10, 9)
edges_input = st.slider("Edges (1-10)", 1, 10, 9)
surface_input = st.slider("Surface (1-10)", 1, 10, 9)

st.divider()

# ===============================
# RUN ANALYSIS
# ===============================

if st.button("Run Pre-Screen Analysis"):

    if not front or not back:
        st.error("Please upload BOTH front and back images.")
    else:

        valid_front, message_front, quality_front = validate_image_quality(front)
        valid_back, message_back, quality_back = validate_image_quality(back)

        if not valid_front:
            st.error(f"Front image issue: {message_front}")
            st.stop()

        if not valid_back:
            st.error(f"Back image issue: {message_back}")
            st.stop()

        overall_quality = min(quality_front, quality_back)

        quality_penalty = 0
        if overall_quality < 80:
            quality_penalty = 0.3

        # FULLY AUTOMATIC CENTERING
        auto_centering_score = estimate_centering(front)

        # Weighted grading (centering is now fully automatic)
       blended_centering = (auto_centering_score * 0.6) + (centering_input * 0.4)

        weighted_grade = (
        blended_centering * 0.35
        + corners_input * 0.25
        + edges_input * 0.20
        + surface_input * 0.20
        )

        mean = round(weighted_grade, 2)

        # Top-end compression
        if mean > 9:
            mean = 9 + (mean - 9) * 0.4

        # Grade ceiling
        lowest_component = min(
            auto_centering_score,
            corners_input,
            edges_input,
            surface_input
        )

        if lowest_component <= 6:
            mean = min(mean, lowest_component + 1)

        if lowest_component <= 5:
            mean = min(mean, lowest_component + 0.5)

        mean = max(mean - quality_penalty, 1)

        # Confidence
        component_variance = np.var([
            auto_centering_score,
            corners_input,
            edges_input,
            surface_input
        ])

        std = round(0.25 + component_variance * 0.1, 2)

        # Elite override
        if (
            auto_centering_score >= 9.8 and
            corners_input == 10 and
            edges_input == 10 and
            surface_input == 10 and
            component_variance == 0
        ):
            mean = 10

        # Gaussian probability
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

        # Upload images
        front_bytes = front.read()
        back_bytes = back.read()

        unique_id = str(uuid.uuid4())

        front_filename = f"{unique_id}_front.jpg"
        back_filename = f"{unique_id}_back.jpg"

        requests.post(
            f"{STORAGE_URL}/card-images/{front_filename}",
            headers={"Authorization": f"Bearer {SUPABASE_KEY}"},
            data=front_bytes
        )

        requests.post(
            f"{STORAGE_URL}/card-images/{back_filename}",
            headers={"Authorization": f"Bearer {SUPABASE_KEY}"},
            data=back_bytes
        )

        front_url = f"{SUPABASE_URL}/storage/v1/object/public/card-images/{front_filename}"
        back_url = f"{SUPABASE_URL}/storage/v1/object/public/card-images/{back_filename}"

        # Display
        st.subheader("Pre-Screen Report")
        st.markdown(f"<h2 style='color:#C9A44D;'>{round(mean,2)}</h2>", unsafe_allow_html=True)
        st.write(f"Auto Centering Score: {auto_centering_score}")
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

        # Save
        data = {
            "manufacturer": manufacturer,
            "stock_type": stock_type,
            "psa10_value": psa10,
            "psa9_value": psa9,
            "psa8_value": psa8,
            "grading_fee": fee,
            "predicted_grade": round(mean,2),
            "prob_10": prob10,
            "prob_9": prob9,
            "prob_8_or_lower": prob8,
            "expected_value": ev,
            "confidence_interval": std,
            "model_version": MODEL_VERSION,
            "submitted_by": user_email,
            "image_quality_score": overall_quality,
            "auto_centering_score": auto_centering_score,
            "front_image_url": front_url,
            "back_image_url": back_url,
            "psa_is_graded": psa_is_graded,
            "psa_actual_grade": psa_actual_grade,
            "created_at": str(datetime.now())
        }

        response = requests.post(TABLE_URL, json=data, headers=headers)

        if response.status_code == 201:
            st.success("Submission saved to database.")
        else:
            st.error(f"Database error: {response.text}")
# ===============================
# ADMIN ANALYTICS PANEL
# ===============================

if user_email == "Adaml":

    st.divider()
    st.header("Admin Analytics Dashboard")

    analytics_response = requests.get(TABLE_URL, headers=headers)

    if analytics_response.status_code == 200:

        records = analytics_response.json()

        if len(records) == 0:
            st.write("No submissions yet.")
        else:

            df = pd.DataFrame(records)

            # ---------------------------
            # Prediction Error Tracking
            # ---------------------------

            if "psa_actual_grade" in df.columns:
                df_with_actual = df.dropna(subset=["psa_actual_grade"])

                if len(df_with_actual) > 0:

                    df_with_actual["prediction_error"] = (
                        df_with_actual["predicted_grade"]
                        - df_with_actual["psa_actual_grade"]
                    )

                    st.subheader("Prediction Accuracy Metrics")

                    st.write(
                        "Mean Absolute Error (MAE):",
                        round(abs(df_with_actual["prediction_error"]).mean(), 2)
                    )

                    st.write(
                        "Average Bias:",
                        round(df_with_actual["prediction_error"].mean(), 2)
                    )

                    st.subheader("Prediction Error Distribution")
                    st.bar_chart(df_with_actual["prediction_error"])

            # ---------------------------
            # Summary Metrics
            # ---------------------------

            st.subheader("Summary Metrics")

            st.write("Total Submissions:", len(df))
            st.write("Average Predicted Grade:", round(df["predicted_grade"].mean(), 2))
            st.write("Average Expected Value:", round(df["expected_value"].mean(), 2))
            st.write("Average Image Quality Score:", round(df["image_quality_score"].mean(), 2))
            st.write("Average Auto Centering Score:", round(df["auto_centering_score"].mean(), 2))

            if "psa_actual_grade" in df.columns:
                st.write(
                    "Average PSA Actual Grade:",
                    round(df["psa_actual_grade"].dropna().mean(), 2)
                )

            st.subheader("Predicted Grade Distribution")
            st.bar_chart(df["predicted_grade"].value_counts().sort_index())

            st.subheader("Stock Type Distribution")
            st.bar_chart(df["stock_type"].value_counts())

            st.subheader("Submissions by User")
            st.bar_chart(df["submitted_by"].value_counts())

            st.subheader("Image Quality Distribution")
            st.bar_chart(df["image_quality_score"].value_counts())

            st.subheader("Raw Dataset")
            st.dataframe(df)

    else:
        st.error("Unable to fetch analytics data.")
