import uuid
from datetime import datetime

import numpy as np
import pandas as pd
import requests
import streamlit as st
from PIL import Image
from streamlit_drawable_canvas import st_canvas

# ============================================================
# DESIGN THEME
# ============================================================

st.set_page_config(page_title="Voodoo Sports Grading", layout="wide")

st.markdown("""
<style>
.stApp {
    background: linear-gradient(90deg,#3F1D6A,#522C87,#5F3A96);
}
h1, h2, h3 {
    color: #C9A44D !important;
}
.stButton>button {
    background-color: #C9A44D !important;
    color: black !important;
    border-radius: 10px !important;
    font-weight: bold !important;
}
label {
    color: white !important;
}
</style>
""", unsafe_allow_html=True)

st.title("VOODOO SPORTS GRADING")

# ============================================================
# CONFIG
# ============================================================

MODEL_VERSION = "v5-overlay-manual-centering"

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
# HELPERS
# ============================================================

def safe_ratio(a: float, b: float) -> float:
    a = float(a)
    b = float(b)
    if a <= 0 or b <= 0:
        return 0.5
    return float(min(a, b) / max(a, b))

def compute_grade(h: float, v: float, edge: float, corner: float) -> float:
    centering_raw = (h + v) / 2
    centering_fixed = 1 - centering_raw

    grade = (
        6.49 +
        4.37 * centering_fixed -
        0.17 * edge +
        4.92 * corner
    )

    if corner < 0.03:
        grade = min(grade, 7.5)
    elif corner < 0.07:
        grade = min(grade, 8.0)

    if edge < 0.002 and corner > 0.05:
        grade = min(grade, 8.2)

    if corner < 0.04:
        grade = min(grade, 7.0)

    return round(max(1, min(10, grade)), 2)

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

def parse_manual_lines(canvas_json, width: int, height: int):
    if not canvas_json or "objects" not in canvas_json:
        return None

    objects = canvas_json["objects"]
    lines = [obj for obj in objects if obj.get("type") == "line"]

    if len(lines) < 4:
        return None

    verticals = []
    horizontals = []

    for line in lines:
        x1 = line["x1"] + line["left"]
        y1 = line["y1"] + line["top"]
        x2 = line["x2"] + line["left"]
        y2 = line["y2"] + line["top"]

        dx = abs(x2 - x1)
        dy = abs(y2 - y1)

        if dy > dx:
            verticals.append((x1 + x2) / 2)
        else:
            horizontals.append((y1 + y2) / 2)

    if len(verticals) < 2 or len(horizontals) < 2:
        return None

    left_x = max(0, min(width, min(verticals)))
    right_x = max(0, min(width, max(verticals)))
    top_y = max(0, min(height, min(horizontals)))
    bottom_y = max(0, min(height, max(horizontals)))

    return left_x, right_x, top_y, bottom_y

def build_initial_lines(width: int, height: int):
    left_x = width * 0.08
    right_x = width * 0.92
    top_y = height * 0.08
    bottom_y = height * 0.92

    return {
        "version": "4.4.0",
        "objects": [
            {
                "type": "line",
                "version": "4.4.0",
                "originX": "left",
                "originY": "top",
                "left": left_x,
                "top": 0,
                "x1": 0,
                "y1": 0,
                "x2": 0,
                "y2": height,
                "stroke": "#00FF00",
                "strokeWidth": 3
            },
            {
                "type": "line",
                "version": "4.4.0",
                "originX": "left",
                "originY": "top",
                "left": right_x,
                "top": 0,
                "x1": 0,
                "y1": 0,
                "x2": 0,
                "y2": height,
                "stroke": "#00FF00",
                "strokeWidth": 3
            },
            {
                "type": "line",
                "version": "4.4.0",
                "originX": "left",
                "originY": "top",
                "left": 0,
                "top": top_y,
                "x1": 0,
                "y1": 0,
                "x2": width,
                "y2": 0,
                "stroke": "#00FF00",
                "strokeWidth": 3
            },
            {
                "type": "line",
                "version": "4.4.0",
                "originX": "left",
                "originY": "top",
                "left": 0,
                "top": bottom_y,
                "x1": 0,
                "y1": 0,
                "x2": width,
                "y2": 0,
                "stroke": "#00FF00",
                "strokeWidth": 3
            }
        ]
    }

# ============================================================
# INTERACTIVE MANUAL CENTERING ASSIST
# ============================================================

st.markdown("## Manual Centering Assist")
use_manual_centering = st.checkbox("Use interactive front centering assist")

manual_left = manual_right = manual_top = manual_bottom = None
manual_h_ratio = manual_v_ratio = None

if use_manual_centering:
    if full_card_front is None:
        st.info("Upload a front image to use interactive centering assist.")
    else:
        try:
            front_image = Image.open(full_card_front).convert("RGB")
        except Exception as e:
            st.error(f"Could not open front image: {e}")
            st.stop()

        max_display_width = 900
        scale = min(1.0, max_display_width / front_image.width)
        display_width = int(front_image.width * scale)
        display_height = int(front_image.height * scale)

        display_image = front_image.resize((display_width, display_height))

        st.caption(
            "Drag the 4 green lines directly on top of the image so they align with "
            "the true measurable front borders."
        )

        canvas_result = st_canvas(
            fill_color="rgba(0, 0, 0, 0)",
            stroke_width=3,
            stroke_color="#00FF00",
            background_image=display_image,
            background_color="rgba(0,0,0,0)",
            update_streamlit=True,
            height=display_height,
            width=display_width,
            drawing_mode="transform",
            initial_drawing=build_initial_lines(display_width, display_height),
            display_toolbar=True,
            key="manual_centering_canvas_overlay",
        )

        parsed = parse_manual_lines(canvas_result.json_data, display_width, display_height)

        if parsed is not None:
            left_x, right_x, top_y, bottom_y = parsed

            manual_left = left_x
            manual_right = display_width - right_x
            manual_top = top_y
            manual_bottom = display_height - bottom_y

            manual_h_ratio = safe_ratio(manual_left, manual_right)
            manual_v_ratio = safe_ratio(manual_top, manual_bottom)

            st.write("Manual Left Border:", round(manual_left, 2))
            st.write("Manual Right Border:", round(manual_right, 2))
            st.write("Manual Top Border:", round(manual_top, 2))
            st.write("Manual Bottom Border:", round(manual_bottom, 2))
            st.write("Manual Horizontal Ratio:", round(manual_h_ratio, 4))
            st.write("Manual Vertical Ratio:", round(manual_v_ratio, 4))
        else:
            st.warning("Move the four guide lines so two are vertical and two are horizontal.")

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

    if use_manual_centering and (manual_h_ratio is None or manual_v_ratio is None):
        st.error("Manual centering assist is enabled, but the guide lines are not set correctly.")
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

    # ---------- MANUAL CENTERING OVERRIDE ----------
    if use_manual_centering:
        h = manual_h_ratio
        v = manual_v_ratio

        st.info("Interactive manual front centering applied")
        st.write("Horizontal Ratio Used:", round(h, 4))
        st.write("Vertical Ratio Used:", round(v, 4))

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
        "created_at": str(datetime.now()),
        "manual_centering_used": use_manual_centering,
        "front_left_measurement": manual_left if use_manual_centering else None,
        "front_right_measurement": manual_right if use_manual_centering else None,
        "front_top_measurement": manual_top if use_manual_centering else None,
        "front_bottom_measurement": manual_bottom if use_manual_centering else None,
        "front_horizontal_ratio_manual": manual_h_ratio if use_manual_centering else None,
        "front_vertical_ratio_manual": manual_v_ratio if use_manual_centering else None,
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
