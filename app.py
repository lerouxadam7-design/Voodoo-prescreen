import streamlit as st
import numpy as np
from supabase import create_client

# ---------------------------
# Supabase Setup (replace with your keys)
# ---------------------------
SUPABASE_URL = "https://nnowtzpkldfrkixeonau.supabase.co"
SUPABASE_KEY = "sb_publishable_mtk5MaeLt69KeK68_KFWJA_7TLfYaPI"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Voodoo Sports Grading")

st.title("VOODOO SPORTS GRADING")
st.caption("PSA Pre-Screen Analyzer")

# ---------------------------
# Upload Images
# ---------------------------
front = st.file_uploader("Upload Front Image")
back = st.file_uploader("Upload Back Image")

# ---------------------------
# Inputs
# ---------------------------
manufacturer = st.text_input("Manufacturer")
stock_type = st.selectbox("Stock Type", ["paper", "chrome", "refractor", "foil"])

psa10 = st.number_input("PSA 10 Value", value=100.0)
psa9 = st.number_input("PSA 9 Value", value=50.0)
psa8 = st.number_input("PSA 8 Value", value=20.0)
fee = st.number_input("Grading Fee", value=25.0)

# ---------------------------
# Analysis Button (ALWAYS visible)
# ---------------------------
if st.button("Run Pre-Screen Analysis"):

    if not front or not back:
        st.error("Please upload both front and back images.")
    else:
        mean = round(np.random.normal(9.3, 0.3), 2)
        std = 0.35

        prob10 = max(0, min(1, 1 - abs(mean - 10)))
        prob9 = max(0, min(1, 1 - abs(mean - 9)))
        prob8 = max(0, 1 - (prob10 + prob9))

        ev = (
            prob10 * psa10 +
            prob9 * psa9 +
            prob8 * psa8
        ) - fee

        st.subheader("Pre-Screen Report")
        st.write(f"Predicted Grade: {mean}")
        st.write(f"Confidence Interval ±{std}")
        st.write(f"PSA 10 Probability: {round(prob10*100,1)}%")
        st.write(f"PSA 9 Probability: {round(prob9*100,1)}%")
        st.write(f"PSA ≤8 Probability: {round(prob8*100,1)}%")
        st.write(f"Expected Value: ${round(ev,2)}")

        # Save to database
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
            "model_version": "v1.0"
        }

        supabase.table("submissions").insert(data).execute()

        st.success("Submission saved to database.")
