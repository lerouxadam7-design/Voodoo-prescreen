import streamlit as st
import requests
import numpy as np
import pandas as pd
from datetime import datetime
import uuid

# ============================================================
# DESIGN THEME
# ============================================================

st.set_page_config(page_title="Voodoo Sports Grading")

st.markdown("""
<style>
.stApp {
    background: linear-gradient(90deg,#3F1D6A,#522C87,#5F3A96);
}
h1, h2, h3 { color: #C9A44D !important; }
.stButton>button {
    background-color: #C9A44D !important;
    color: black !important;
    border-radius: 10px !important;
    font-weight: bold !important;
}
label { color: white !important; }
</style>
""", unsafe_allow_html=True)

st.title("VOODOO SPORTS GRADING")

# ============================================================
# CONFIG
# ============================================================

MODEL_VERSION = "v3-linear-locked"

SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
API_BASE = "https://voodoo-centering-api.onrender.com"

TABLE_URL = f"{SUPABASE_URL}/rest/v1/submissions"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

upload_headers = {
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "apikey": SUPABASE_KEY,
    "Content-Type": "image/jpeg"
}

# ============================================================
# AUTHORIZATION
# ============================================================

st.markdown("### Access")
user_email = st.text_input("Enter Access Email")

if user_email:
    user_check = requests.get(
        f"{SUPABASE_URL}/rest/v1/authorized_users?email=eq.{user_email}",
        headers=headers
    )
    user_data = user_check.json()

    if len(user_data) == 0:
        st.warning("Access restricted")
        st.stop()

    user_role = user_data[0]["role"]
else:
    st.stop()

# ============================================================
# CARD INFO
# ============================================================

st.markdown("## Card Information")

manufacturer = st.text_input("Manufacturer")
stock_type = st.selectbox(
    "Stock Type",
    ["paper", "chrome", "refractor", "foil", "other"]
)

psa_is_graded = st.checkbox("PSA graded?")
psa_actual_grade = None

if psa_is_graded:
    psa_actual_grade = st.number_input("PSA Grade", 1.0, 10.0, step=0.5)

# ============================================================
# IMAGE INPUTS
# ============================================================

st.markdown("## Upload Card Images")

full_card_front = st.file_uploader("Front Image", ["jpg","jpeg","png"])
full_card_back = st.file_uploader("Back Image", ["jpg","jpeg","png"])

st.markdown("### Corner Images (2 Required)")

corner1 = st.file_uploader("Corner 1 (Required)", ["jpg","jpeg","png"])
corner2 = st.file_uploader("Corner 2 (Required)", ["jpg","jpeg","png"])
corner3 = st.file_uploader("Corner 3 (Optional)", ["jpg","jpeg","png"])
corner4 = st.file_uploader("Corner 4 (Optional)", ["jpg","jpeg","png"])

# ============================================================
# MODEL
# ============================================================

def compute_grade(h, v, edge, corner):
    centering_raw = (h + v) / 2
    centering_fixed = 1 - centering_raw

    grade = (
        6.49 +
        4.37 * centering_fixed -
        0.17 * edge +
        4.92 * corner
    )
    return round(max(1, min(10, grade)), 2)

# ============================================================
# DECISION PANEL
# ============================================================

def decision_panel(grade, h, v, edge, corner):

    if grade >= 9.2:
        st.success("STRONG SUBMIT")
    elif grade >= 8.5:
        st.success("SUBMIT")
    elif grade >= 7.5:
        st.warning("BORDERLINE")
    else:
        st.error("DO NOT SUBMIT")

    confidence = float(np.clip(1 - abs(h - v), 0, 1))
    st.write("Confidence:", round(confidence, 2))

    st.markdown("### Why")
    st.write("Centering Impact:", round(1 - ((h+v)/2),3))
    st.write("Corner Impact:", round(1-corner,3))
    st.write("Edge Impact:", round(1-edge,3))

# ============================================================
# RUN ANALYSIS
# ============================================================

if st.button("Run Analysis"):

    if full_card_front is None:
        st.error("Front image required")
        st.stop()

    if corner1 is None or corner2 is None:
        st.error("2 corner images required")
        st.stop()

    # FULL CARD API
    r = requests.post(
        f"{API_BASE}/analyze",
        files={"file": full_card_front.getvalue()}
    )

    if r.status_code != 200:
        st.error(f"Analyze API failed: {r.text}")
        st.stop()

    data = r.json()

    h = data["horizontal_ratio"]
    v = data["vertical_ratio"]
    edge = data["edge_score"]

    # CORNER API (SAFE)
    corner_files = [corner1, corner2]
    if corner3: corner_files.append(corner3)
    if corner4: corner_files.append(corner4)

    scores = []

    for c in corner_files:

        cr = requests.post(
            f"{API_BASE}/analyze_corner",
            files={"file": c.getvalue()}
        )

        if cr.status_code != 200:
            st.error(f"Corner API failed: {cr.text}")
            continue

        try:
            scores.append(cr.json()["corner_score"])
        except:
            st.error("Invalid corner response")
            continue

    if len(scores) == 0:
        corner = 0.5
    else:
        corner = min(scores)

    # GRADE
    grade = compute_grade(h, v, edge, corner)

    st.markdown("## Grade")
    st.markdown(f"### {grade}")

    decision_panel(grade, h, v, edge, corner)

    # ========================================================
    # SAVE IMAGES
    # ========================================================

    card_id = str(uuid.uuid4())

    front_name = f"{card_id}_front.jpg"
    back_name = f"{card_id}_back.jpg"

    requests.post(
        f"{SUPABASE_URL}/storage/v1/object/card-images/{front_name}",
        headers=upload_headers,
        data=full_card_front.getvalue()
    )

    if full_card_back:
        requests.post(
            f"{SUPABASE_URL}/storage/v1/object/card-images/{back_name}",
            headers=upload_headers,
            data=full_card_back.getvalue()
        )

    front_url = f"{SUPABASE_URL}/storage/v1/object/public/card-images/{front_name}"
    back_url = f"{SUPABASE_URL}/storage/v1/object/public/card-images/{back_name}" if full_card_back else None

    # SAVE DATA
    payload = {
        "card_id": card_id,
        "manufacturer": manufacturer,
        "stock_type": stock_type,
        "psa_is_graded": psa_is_graded,
        "psa_actual_grade": psa_actual_grade,
        "horizontal_ratio": h,
        "vertical_ratio": v,
        "edge_score": edge,
        "corner_score": corner,
        "calibrated_grade": grade,
        "front_image_url": front_url,
        "back_image_url": back_url,
        "submitted_by": user_email,
        "created_at": str(datetime.now())
    }

    requests.post(TABLE_URL, json=payload, headers=headers)

    st.success("Saved successfully")

# ============================================================
# ADMIN
# ============================================================

if user_role == "admin":

    st.markdown("---")
    st.markdown("## Admin Dashboard")

    df = pd.DataFrame(requests.get(TABLE_URL, headers=headers).json())

    st.write("Total:", len(df))

    if "psa_actual_grade" in df.columns:
        dfv = df.dropna(subset=["psa_actual_grade","calibrated_grade"]).copy()

        if len(dfv):
            dfv["error"] = dfv["calibrated_grade"] - dfv["psa_actual_grade"]

            st.write("MAE:", round(abs(dfv["error"]).mean(),3))
            st.write("Bias:", round(dfv["error"].mean(),3))

            st.bar_chart(dfv["error"])
