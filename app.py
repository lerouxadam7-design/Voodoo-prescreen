import streamlit as st
import requests
import numpy as np
from datetime import datetime
import uuid

# ============================================================
# CONFIG
# ============================================================

MODEL_VERSION = "v2-experimental"

SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]

API_BASE = "https://YOUR-RENDER-API.onrender.com"  # <-- Replace with yours

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
st.title("Voodoo Sports Grading — RAW Pre-Screen")

st.markdown("""
Upload:
• Full card front (required)  
• Full card back (recommended)  
• Corner close-ups (optional but improves accuracy)
""")

# ============================================================
# FILE UPLOADS
# ============================================================

full_card_front = st.file_uploader("Full Card - Front", type=["jpg", "jpeg", "png"])
full_card_back = st.file_uploader("Full Card - Back", type=["jpg", "jpeg", "png"])

st.markdown("### Optional Corner Close-Ups (Front Only)")

corner1 = st.file_uploader("Corner 1", type=["jpg","jpeg","png"], key="corner1")
corner2 = st.file_uploader("Corner 2", type=["jpg","jpeg","png"], key="corner2")
corner3 = st.file_uploader("Corner 3", type=["jpg","jpeg","png"], key="corner3")
corner4 = st.file_uploader("Corner 4", type=["jpg","jpeg","png"], key="corner4")

corner_files = [c for c in [corner1, corner2, corner3, corner4] if c is not None]

if len(corner_files) == 0:
    st.info("Corner close-ups improve grading accuracy but are optional during calibration.")

# ============================================================
# EXPERIMENTAL GRADE FUNCTION
# ============================================================

def compute_experimental_grade(horizontal_ratio, vertical_ratio, edge_score, corner_score):

    centering_raw = (horizontal_ratio + vertical_ratio) / 2
    centering_score = 10 - ((1 - centering_raw) * 5)
    centering_score = max(1, min(10, centering_score))

    edge_score_scaled = max(1, min(10, edge_score * 10))
    corner_score_scaled = max(1, min(10, corner_score * 10))

    lowest = min(centering_score, edge_score_scaled, corner_score_scaled)

    if lowest <= 5:
        final = lowest + 0.5
    elif lowest <= 6:
        final = lowest + 1
    else:
        final = (
            centering_score * 0.3 +
            corner_score_scaled * 0.4 +
            edge_score_scaled * 0.3
        )

    if (
        centering_score >= 9 and
        corner_score_scaled >= 9 and
        edge_score_scaled >= 9
    ):
        final = 10

    return round(min(final, 10), 2), centering_score, edge_score_scaled, corner_score_scaled

# ============================================================
# RUN ANALYSIS
# ============================================================

if st.button("Run Analysis"):

    if full_card_front is None:
        st.error("Front card image is required.")
        st.stop()

    # --------------------------------------------------------
    # FULL CARD ANALYSIS (FRONT ONLY)
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
    # CORNER ANALYSIS (OPTIONAL)
    # --------------------------------------------------------

    corner_score = 0.5

    if len(corner_files) > 0:

        corner_scores = []

        for c in corner_files:
            response_corner = requests.post(
                f"{API_BASE}/analyze_corner",
                files={"file": c.getvalue()}
            )

            if response_corner.status_code == 200:
                data_corner = response_corner.json()
                corner_scores.append(data_corner["corner_score"])

        if len(corner_scores) > 0:
            corner_score = float(np.mean(corner_scores))

    # --------------------------------------------------------
    # COMPUTE EXPERIMENTAL GRADE
    # --------------------------------------------------------

    experimental_grade, centering_component, edge_component, corner_component = compute_experimental_grade(
        horizontal_ratio,
        vertical_ratio,
        edge_score,
        corner_score
    )

    # ========================================================
    # DISPLAY RESULTS
    # ========================================================

    st.markdown("## Experimental Grade (v2)")
    st.markdown(f"### {experimental_grade}")

    st.markdown("---")
    st.markdown("### Component Scores")

    st.write("Centering:", round(centering_component, 2))
    st.write("Edges:", round(edge_component, 2))
    st.write("Corners:", round(corner_component, 2))

    st.markdown("---")
    st.markdown("### Raw Feature Values")

    st.write("Horizontal Ratio:", round(horizontal_ratio, 4))
    st.write("Vertical Ratio:", round(vertical_ratio, 4))
    st.write("Edge Score (raw):", round(edge_score, 4))
    st.write("Corner Score (raw):", round(corner_score, 4))

    # ========================================================
    # SAVE IMAGES TO SUPABASE STORAGE
    # ========================================================

    card_id = str(uuid.uuid4())

    upload_headers = {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "apikey": SUPABASE_KEY,
        "Content-Type": "image/jpeg"
    }

    front_filename = f"{card_id}_front.jpg"
    back_filename = f"{card_id}_back.jpg"

    # Upload front
    requests.post(
        f"{SUPABASE_URL}/storage/v1/object/card-images/{front_filename}",
        headers=upload_headers,
        data=full_card_front.getvalue()
    )

    # Upload back if provided
    if full_card_back is not None:
        requests.post(
            f"{SUPABASE_URL}/storage/v1/object/card-images/{back_filename}",
            headers=upload_headers,
            data=full_card_back.getvalue()
        )

    front_url = f"{SUPABASE_URL}/storage/v1/object/public/card-images/{front_filename}"
    back_url = f"{SUPABASE_URL}/storage/v1/object/public/card-images/{back_filename}" if full_card_back else None

    # ========================================================
    # SAVE METADATA TO SUPABASE TABLE
    # ========================================================

    data = {
        "card_id": card_id,
        "model_version": MODEL_VERSION,
        "horizontal_ratio": horizontal_ratio,
        "vertical_ratio": vertical_ratio,
        "edge_score": edge_score,
        "corner_score": corner_score,
        "centering_component": centering_component,
        "edge_component": edge_component,
        "corner_component": corner_component,
        "experimental_grade": experimental_grade,
        "front_image_url": front_url,
        "back_image_url": back_url,
        "created_at": str(datetime.now())
    }

    save_response = requests.post(TABLE_URL, json=data, headers=headers)

    if save_response.status_code == 201:
        st.success("Submission saved to database.")
    else:
        st.error(f"Database error: {save_response.text}")
