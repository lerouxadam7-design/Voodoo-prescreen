import streamlit as st
import numpy as np
import pandas as pd
from datetime import datetime
from supabase import create_client
import streamlit as st

SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
st.set_page_config(page_title="Voodoo Sports Grading")

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

# ---------------------------
# Run Analysis
# ---------------------------
if st.button("Run Pre-Screen Analysis"):

    if not front or not back:
        st.error("Please upload BOTH front and back images.")
    else:
        # Simulated model (stable placeholder)
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

        st.write("### Expected Value")

        if ev > 0:
            st.success(f"Projected Profit: +${round(ev,2)}")
        else:
            st.error(f"Projected Loss: -${abs(round(ev,2))}")

        # Save locally in session (temporary data collection)
        if "submissions" not in st.session_state:
            st.session_state.submissions = []

        st.session_state.submissions.append({
            "timestamp": datetime.now(),
            "manufacturer": manufacturer,
            "stock_type": stock_type,
            "predicted_grade": mean,
            "prob_10": prob10,
            "prob_9": prob9,
            "prob_8_or_lower": prob8,
            "expected_value": ev
        })

        st.success("Submission saved (local session).")
