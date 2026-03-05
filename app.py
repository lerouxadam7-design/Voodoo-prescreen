import streamlit as st
import requests
import numpy as np
import pandas as pd
from datetime import datetime
import uuid

# ============================================================
# CONFIG
# ============================================================

MODEL_VERSION = "v3-calibrated"

SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]

API_BASE = "https://voodoo-centering-api.onrender.com"  # Replace

TABLE_URL = f"{SUPABASE_URL}/rest/v1/submissions"
STORAGE_URL = f"{SUPABASE_URL}/storage/v1/object"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# ============================================================
# PAGE SETUP
# ============================================================

st.set_page_config(page_title="Voodoo Sports Grading")
st.title("Voodoo Sports Grading")

st.warning("During calibration phase, slabbed PSA cards help improve grading accuracy.")

# ============================================================
# FILE UPLOADS
# ============================================================

st.markdown("## Upload Card")

full_card_front = st.file_uploader("Full Card - Front", type=["jpg", "jpeg", "png"])
full_card_back = st.file_uploader("Full Card - Back", type=["jpg", "jpeg", "png"])

st.markdown("### Optional Corner Close-Ups (Front Only)")

corner1 = st.file_uploader("Corner 1", type=["jpg","jpeg","png"], key="corner1")
corner2 = st.file_uploader("Corner 2", type=["jpg","jpeg","png"], key="corner2")
corner3 = st.file_uploader("Corner 3", type=["jpg","jpeg","png"], key="corner3")
corner4 = st.file_uploader("Corner 4", type=["jpg","jpeg","png"], key="corner4")

corner_files = [c for c in [corner1, corner2, corner3, corner4] if c is not None]

if len(corner_files) == 0:
    st.info("Corner close-ups improve grading accuracy but are optional.")

# ============================================================
# GRADE FUNCTIONS
# ============================================================

def compute_experimental_grade(horizontal_ratio, vertical_ratio, edge_score, corner_score):

    centering_raw = (horizontal_ratio + vertical_ratio) / 2
    centering_score = 10 - ((1 - centering_raw) * 5)

    edge_score_scaled = edge_score * 20
    corner_score_scaled = corner_score * 20

    final = (
        centering_score * 0.4 +
        corner_score_scaled * 0.4 +
        edge_score_scaled * 0.2
    )

    return round(max(1, min(10, final)), 2)


def compute_calibrated_grade(horizontal_ratio, vertical_ratio, edge_score, corner_score):

    centering_raw = (horizontal_ratio + vertical_ratio) / 2
    centering_fixed = 1 - centering_raw

    grade = (
        6.49
        + 4.37 * centering_fixed
        - 0.17 * edge_score
        + 4.92 * corner_score
    )

    return round(max(1, min(10, grade)), 2)

# ============================================================
# RUN ANALYSIS
# ============================================================

if st.button("Run Analysis"):

    if full_card_front is None:
        st.error("Front card image is required.")
        st.stop()

    # --------------------------------------------------------
    # FULL CARD ANALYSIS
    # --------------------------------------------------------

    response = requests.post(
        f"{API_BASE}/analyze",
        files={"file": full_card_front.getvalue()}
    )

    if response.status_code != 200:
        st.error("Full card analysis failed.")
        st.stop()

    full_result = response.json()

    horizontal_ratio = full_result["horizontal_ratio"]
    vertical_ratio = full_result["vertical_ratio"]
    edge_score = full_result["edge_score"]

    # --------------------------------------------------------
    # CORNER ANALYSIS
    # --------------------------------------------------------

    corner_score = 0.5

    if len(corner_files) > 0:
        scores = []

        for c in corner_files:
            r = requests.post(
                f"{API_BASE}/analyze_corner",
                files={"file": c.getvalue()}
            )
            if r.status_code == 200:
                scores.append(r.json()["corner_score"])

        if len(scores) > 0:
            corner_score = float(np.mean(scores))

    # --------------------------------------------------------
    # GRADES
    # --------------------------------------------------------

    experimental_grade = compute_experimental_grade(
        horizontal_ratio,
        vertical_ratio,
        edge_score,
        corner_score
    )

    calibrated_grade = compute_calibrated_grade(
        horizontal_ratio,
        vertical_ratio,
        edge_score,
        corner_score
    )

    # ========================================================
    # DISPLAY RESULTS
    # ========================================================

    st.markdown("## Calibrated Grade (v3)")
    st.markdown(f"### {calibrated_grade}")

    st.markdown("## Experimental Grade (v2)")
    st.markdown(f"### {experimental_grade}")

    st.markdown("---")
    st.markdown("### Raw Feature Values")

    st.write("Horizontal Ratio:", round(horizontal_ratio, 4))
    st.write("Vertical Ratio:", round(vertical_ratio, 4))
    st.write("Edge Score:", round(edge_score, 4))
    st.write("Corner Score:", round(corner_score, 4))

    # ========================================================
    # SAVE TO SUPABASE
    # ========================================================

    card_id = str(uuid.uuid4())

    data = {
        "card_id": card_id,
        "model_version": MODEL_VERSION,
        "horizontal_ratio": horizontal_ratio,
        "vertical_ratio": vertical_ratio,
        "edge_score": edge_score,
        "corner_score": corner_score,
        "experimental_grade": experimental_grade,
        "calibrated_grade": calibrated_grade,
        "created_at": str(datetime.now())
    }

    save = requests.post(TABLE_URL, json=data, headers=headers)

    if save.status_code == 201:
        st.success("Submission saved.")
    else:
        st.error("Database error.")

# ============================================================
# ADMIN DASHBOARD
# ============================================================

st.markdown("---")
st.markdown("## Admin Dashboard")

analytics_response = requests.get(TABLE_URL, headers=headers)

if analytics_response.status_code == 200:

    df = pd.DataFrame(analytics_response.json())

    if len(df) > 0:

        st.write("Total Submissions:", len(df))

        if "psa_actual_grade" in df.columns:

            df_valid = df.dropna(subset=["psa_actual_grade", "calibrated_grade"])

            if len(df_valid) > 0:

                df_valid["error"] = df_valid["calibrated_grade"] - df_valid["psa_actual_grade"]

                mae = abs(df_valid["error"]).mean()
                bias = df_valid["error"].mean()

                st.subheader("Calibration Metrics")
                st.write("MAE:", round(mae, 3))
                st.write("Bias:", round(bias, 3))

                st.subheader("Error Distribution")
                st.bar_chart(df_valid["error"])

        st.subheader("Grade Distribution")
        st.bar_chart(df["calibrated_grade"].value_counts().sort_index())
