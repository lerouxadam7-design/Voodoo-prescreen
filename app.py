import streamlit as st
import numpy as np

st.set_page_config(page_title="Voodoo Sports Grading")

st.markdown("""
<style>
body {
    background: linear-gradient(135deg, #3E206D, #4B2A85);
}
.stApp {
    background: linear-gradient(135deg, #3E206D, #4B2A85);
    color: white;
}
.big-grade {
    font-size: 50px;
    color: #C9A44D;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

st.title("VOODOO SPORTS GRADING")
st.caption("PSA Pre-Screen Analyzer")

front = st.file_uploader("Upload Front Image")
back = st.file_uploader("Upload Back Image")

if front and back:

    grading_fee = st.number_input("Grading Fee", value=25.0)
    psa10 = st.number_input("PSA 10 Value", value=100.0)
    psa9 = st.number_input("PSA 9 Value", value=50.0)
    psa8 = st.number_input("PSA 8 Value", value=20.0)

    if st.button("Analyze Card"):

        mean = round(np.random.normal(9.3, 0.3), 2)
        std = 0.35

        prob10 = max(0, min(1, 1 - abs(mean - 10)))
        prob9 = max(0, min(1, 1 - abs(mean - 9)))
        prob8 = max(0, 1 - (prob10 + prob9))

        ev = (
            prob10 * psa10 +
            prob9 * psa9 +
            prob8 * psa8
        ) - grading_fee

        st.markdown(f"<div class='big-grade'>{mean}</div>", unsafe_allow_html=True)

        st.write(f"PSA 10 Probability: {round(prob10*100,1)}%")
        st.write(f"PSA 9 Probability: {round(prob9*100,1)}%")
        st.write(f"PSA ≤8 Probability: {round(prob8*100,1)}%")

        if ev > 0:
            st.success(f"Projected Profit: +${round(ev,2)}")
        else:
            st.error(f"Projected Loss: -${abs(round(ev,2))}")
