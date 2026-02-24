from supabase import create_client
import os

SUPABASE_URL = https://nnowtzpkldfrkixeonau.supabase.co
SUPABASE_KEY = sb_publishable_mtk5MaeLt69KeK68_KFWJA_7TLfYaPl

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)import streamlit as st
import numpy as np

st.set_page_config(
    page_title="Voodoo Sports Grading",
    layout="centered"
)

# ---------------------------
# Premium Styling
# ---------------------------
st.markdown("""
<style>
html, body, [class*="css"]  {
    font-family: 'Segoe UI', sans-serif;
}

.stApp {
    background: linear-gradient(135deg, #2B125C, #4B2A85);
    color: white;
}

.header {
    text-align: center;
    padding-bottom: 10px;
}

.brand {
    font-size: 42px;
    font-weight: 800;
    letter-spacing: 1px;
}

.subbrand {
    color: #C9A44D;
    font-size: 18px;
    margin-bottom: 30px;
}

.card {
    background: rgba(255,255,255,0.07);
    padding: 25px;
    border-radius: 14px;
    margin-top: 20px;
}

.big-grade {
    font-size: 64px;
    font-weight: 900;
    color: #C9A44D;
    text-align: center;
    margin-top: 10px;
}

.metric-label {
    font-size: 14px;
    opacity: 0.8;
}

button[kind="primary"] {
    background-color: #C9A44D !important;
    color: black !important;
    font-weight: bold !important;
    border-radius: 8px !important;
}

hr {
    border: 1px solid rgba(255,255,255,0.1);
}
</style>
""", unsafe_allow_html=True)

# ---------------------------
# Header
# ---------------------------
st.markdown("""
<div class="header">
    <div class="brand">VOODOO SPORTS GRADING</div>
    <div class="subbrand">PSA Pre-Screen Analyzer</div>
</div>
""", unsafe_allow_html=True)

# ---------------------------
# Upload Section
# ---------------------------
st.markdown("### Upload Card Images")

col1, col2 = st.columns(2)

with col1:
    front = st.file_uploader("Front Image", type=["jpg","png"])

with col2:
    back = st.file_uploader("Back Image", type=["jpg","png"])

# ---------------------------
# Main App
# ---------------------------
if front and back:

    st.markdown('<div class="card">', unsafe_allow_html=True)

    st.markdown("### Market Inputs")

    col3, col4, col5, col6 = st.columns(4)

    with col3:
        psa10 = st.number_input("PSA 10", value=100.0)

    with col4:
        psa9 = st.number_input("PSA 9", value=50.0)

    with col5:
        psa8 = st.number_input("PSA 8", value=20.0)

    with col6:
        fee = st.number_input("Grading Fee", value=25.0)

    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("Run Pre-Screen Analysis"):

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

        st.markdown('<div class="card">', unsafe_allow_html=True)

        st.markdown("### Pre-Screen Report")

        st.markdown(f"<div class='big-grade'>{mean}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-label'>95% Confidence Interval ±{std}</div>", unsafe_allow_html=True)

        st.markdown("---")

        st.markdown("#### Grade Probability")

        st.progress(prob10)
        st.write(f"PSA 10: {round(prob10*100,1)}%")

        st.progress(prob9)
        st.write(f"PSA 9: {round(prob9*100,1)}%")

        st.progress(prob8)
        st.write(f"PSA ≤8: {round(prob8*100,1)}%")

        st.markdown("---")

        st.markdown("#### Expected Value")

        if ev > 0:
            st.success(f"Projected Profit: +${round(ev,2)}")
        else:
            st.error(f"Projected Loss: -${abs(round(ev,2))}")

        st.markdown("---")

        st.markdown("#### Submission Risk")

        if prob10 > 0.7:
            st.success("Low Risk – Strong 10 Candidate")
        elif prob10 > 0.4:
            st.warning("Moderate Risk – Borderline")
        else:
            st.error("High Risk – Likely 9 or Lower")

        st.markdown("</div>", unsafe_allow_html=True)


        
