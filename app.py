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

MODEL_VERSION = "v3-raw-corner-boost"

SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
API_BASE = "https://voodoo-centering-api.onrender.com"  # replace with your real URL

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
        headers=headers,
        timeout=30
    )

    if user_check.status_code != 200:
        st.error("User lookup failed")
        st.stop()

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

full_card_front = st.file_uploader("Front Image", ["jpg", "jpeg", "png"])
full_card_back = st.file_uploader("Back Image", ["jpg", "jpeg", "png"])

st.markdown("### Corner Images (2 Required)")
corner1 = st.file_uploader("Corner 1 (Required)", ["jpg", "jpeg", "png"], key="corner1")
corner2 = st.file_uploader("Corner 2 (Required)", ["jpg", "jpeg", "png"], key="corner2")
corner3 = st.file_uploader("Corner 3 (Optional)", ["jpg", "jpeg", "png"], key="corner3")
corner4 = st.file_uploader("Corner 4 (Optional)", ["jpg", "jpeg", "png"], key="corner4")

# ============================================================
# MODEL
# ============================================================

def compute_grade(h: float, v: float, edge: float, corner: float) -> float:
    centering_raw = (h + v) / 2
    centering_fixed = 1 - centering_raw

    # stronger corner influence for raw cards
    grade = (
        6.49
        + 4.37 * centering_fixed
        - 0.17 * edge
        + 8.0 * corner
    )

    # hard floor cap for very weak corners
    if corner < 0.05:
        grade = min(grade, 7.5)

    return round(max(1, min(10, grade)), 2)

# ============================================================
# DECISION PANEL
# ============================================================

def decision_panel(grade: float, h: float, v: float, edge: float, corner: float) -> None:
    if grade >= 9.2:
        st.success("STRONG SUBMIT")
    elif grade >= 8.5:
        st.success("SUBMIT")
    elif grade >= 7.5:
        st.warning("BORDERLINE")
    else:
        st.error("DO NOT SUBMIT")

    confidence = float(np.clip(1 - abs(h - v), 0, 1))
    if confidence > 0.85:
        risk = "Low"
    elif confidence > 0.65:
        risk = "Moderate"
    else:
        risk = "High"

    st.write("Confidence:", round(confidence, 2))
    st.write("Risk Level:", risk)

    st.markdown("### Why")
    st.write("Centering Impact:", round(1 - ((h + v) / 2), 3))
    st.write("Corner Impact:", round(1 - corner, 3))
    st.write("Edge Impact:", round(1 - edge, 3))

# ============================================================
# RUN ANALYSIS
# ============================================================

if st.button("Run Analysis"):

    if full_card_front is None:
        st.error("Front image required")
        st.stop()

    if corner1 is None or corner2 is None:
        st.error("At least 2 corner images are required")
        st.stop()

    # ---------- FULL CARD API ----------
    try:
        r = requests.post(
            f"{API_BASE}/analyze",
            files={"file": full_card_front.getvalue()},
            timeout=60
        )
    except Exception as e:
        st.error(f"Analyze API request failed: {e}")
        st.stop()

    if r.status_code != 200:
        st.error(f"Analyze API failed: {r.text}")
        st.stop()

    try:
        data = r.json()
    except Exception:
        st.error(f"Analyze API returned invalid JSON: {r.text}")
        st.stop()

    if "error" in data:
        st.error(f"Analyze API error: {data['error']}")
        st.stop()

    h = data["horizontal_ratio"]
    v = data["vertical_ratio"]
    edge = data["edge_score"]

    # ---------- CORNER API ----------
    corner_files = [corner1, corner2]
    if corner3 is not None:
        corner_files.append(corner3)
    if corner4 is not None:
        corner_files.append(corner4)

    scores = []

    for c in corner_files:
        try:
            cr = requests.post(
                f"{API_BASE}/analyze_corner",
                files={"file": c.getvalue()},
                timeout=60
            )
        except Exception as e:
            st.error(f"Corner API request failed: {e}")
            continue

        if cr.status_code != 200:
            st.error(f"Corner API failed: {cr.text}")
            continue

        try:
            corner_data = cr.json()
        except Exception:
            st.error(f"Invalid corner response: {cr.text}")
            continue

        if "error" in corner_data:
            st.error(f"Corner API error: {corner_data['error']}")
            continue

        scores.append(corner_data["corner_score"])

    if len(scores) == 0:
        corner = 0.5
        st.warning("All corner analyses failed. Using neutral corner score.")
    else:
        # PSA logic: weakest corner dominates
        corner = min(scores)

    # ---------- GRADE ----------
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

    front_upload = requests.post(
        f"{SUPABASE_URL}/storage/v1/object/card-images/{front_name}",
        headers=upload_headers,
        data=full_card_front.getvalue(),
        timeout=60
    )
    if front_upload.status_code not in [200, 201]:
        st.error(f"Front upload failed: {front_upload.text}")

    if full_card_back:
        back_upload = requests.post(
            f"{SUPABASE_URL}/storage/v1/object/card-images/{back_name}",
            headers=upload_headers,
            data=full_card_back.getvalue(),
            timeout=60
        )
        if back_upload.status_code not in [200, 201]:
            st.error(f"Back upload failed: {back_upload.text}")

    front_url = f"{SUPABASE_URL}/storage/v1/object/public/card-images/{front_name}"
    back_url = (
        f"{SUPABASE_URL}/storage/v1/object/public/card-images/{back_name}"
        if full_card_back else None
    )

    # ========================================================
    # SAVE DATA
    # ========================================================

    payload = {
        "card_id": card_id,
        "model_version": MODEL_VERSION,
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

    save_response = requests.post(TABLE_URL, json=payload, headers=headers, timeout=30)

    if save_response.status_code in [200, 201]:
        st.success("Saved successfully")
    else:
        st.error(f"Database save failed: {save_response.text}")

# ============================================================
# ADMIN
# ============================================================

if user_role == "admin":
    st.markdown("---")
    st.markdown("## Admin Dashboard")

    try:
        admin_resp = requests.get(TABLE_URL, headers=headers, timeout=30)
        admin_resp.raise_for_status()
        df = pd.DataFrame(admin_resp.json())
    except Exception as e:
        st.error(f"Failed to load admin data: {e}")
        st.stop()

    st.write("Total:", len(df))

    if "psa_actual_grade" in df.columns and "calibrated_grade" in df.columns:
        dfv = df.dropna(subset=["psa_actual_grade", "calibrated_grade"]).copy()

        if len(dfv):
            dfv.loc[:, "error"] = dfv["calibrated_grade"] - dfv["psa_actual_grade"]

            st.write("MAE:", round(abs(dfv["error"]).mean(), 3))
            st.write("Bias:", round(dfv["error"].mean(), 3))

            st.bar_chart(dfv["error"])

    st.markdown("---")
    st.markdown("## Model Maintenance")

    if st.button("Re-Score All Cards"):
        for _, row in df.iterrows():
            if pd.isna(row.get("horizontal_ratio")) or pd.isna(row.get("vertical_ratio")):
                continue

            new_grade = compute_grade(
                float(row["horizontal_ratio"]),
                float(row["vertical_ratio"]),
                float(row["edge_score"]),
                float(row["corner_score"])
            )

            new_data = {
                "card_id": row["card_id"],
                "model_version": MODEL_VERSION,
                "manufacturer": row.get("manufacturer"),
                "stock_type": row.get("stock_type"),
                "psa_is_graded": row.get("psa_is_graded"),
                "psa_actual_grade": row.get("psa_actual_grade"),
                "horizontal_ratio": row["horizontal_ratio"],
                "vertical_ratio": row["vertical_ratio"],
                "edge_score": row["edge_score"],
                "corner_score": row["corner_score"],
                "calibrated_grade": new_grade,
                "front_image_url": row.get("front_image_url"),
                "back_image_url": row.get("back_image_url"),
                "submitted_by": user_email,
                "created_at": str(datetime.now())
            }

            requests.post(TABLE_URL, json=new_data, headers=headers, timeout=30)

        st.success("Re-scored under locked model.")
