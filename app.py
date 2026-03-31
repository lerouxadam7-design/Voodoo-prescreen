import base64
import io
import uuid
from datetime import datetime

import numpy as np
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image

# ============================================================
# DESIGN THEME
# ============================================================

st.set_page_config(page_title="Voodoo Sports Grading", layout="wide")

st.markdown("""
<style>

/* Background */
.stApp {
    background: linear-gradient(90deg, #3F1D6A, #522C87, #5F3A96);
}

/* Default text white */
html, body, [class*="css"] {
    color: white !important;
}

/* Headings gold */
h1, h2, h3, h4, h5, h6 {
    color: #C9A44D !important;
}

/* Labels / markdown / captions white */
label, p, span, div, .stMarkdown {
    color: white !important;
}

.small-note {
    color: #dddddd !important;
    font-size: 0.9rem;
}

/* Keep typeable text black */
input, textarea {
    color: black !important;
    -webkit-text-fill-color: black !important;
    background-color: white !important;
}

input::placeholder, textarea::placeholder {
    color: #444 !important;
    -webkit-text-fill-color: #444 !important;
}

[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stTextArea"] textarea {
    color: black !important;
    -webkit-text-fill-color: black !important;
    background-color: white !important;
}

/* Selectbox text black */
div[data-baseweb="select"] * {
    color: black !important;
}

/* Buttons */
.stButton > button {
    background-color: #C9A44D !important;
    color: black !important;
    border-radius: 10px !important;
    font-weight: bold !important;
}

/* Tables */
thead tr th,
tbody tr td {
    color: white !important;
}

/* Metrics */
[data-testid="stMetricValue"],
[data-testid="stMetricLabel"] {
    color: white !important;
}

</style>
""", unsafe_allow_html=True)

st.title("VOODOO SPORTS GRADING")

# ============================================================
# CONFIG
# ============================================================

MODEL_VERSION = "v6.3-low-grade-correction"

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


def ratio_to_psa_centering(ratio: float) -> str:
    ratio = max(0.01, min(1.0, float(ratio)))
    major = 100 / (1 + ratio)
    minor = 100 - major
    major = round(major)
    minor = round(minor)
    low = min(major, minor)
    high = max(major, minor)
    return f"{low}/{high}"


def centering_psa_grade(h: float, v: float) -> float:
    worst = min(float(h), float(v))

    if worst >= 0.90:
        return 10.0
    if worst >= 0.84:
        return 9.5
    if worst >= 0.80:
        return 9.0
    if worst >= 0.72:
        return 8.0
    if worst >= 0.64:
        return 7.0
    return 6.0


def remap_corner_for_model(corner: float) -> float:
    c = max(0.0, min(1.0, float(corner)))
    return float(np.clip(np.sqrt(c), 0, 1))


def corner_subgrade(corner: float) -> float:
    c_adj = remap_corner_for_model(corner)
    score = 7.0 + (c_adj * 3.0)
    return round(max(1, min(10, score)), 2)


def edge_subgrade(edge: float) -> float:
    e = max(0.0, min(1.0, float(edge)))
    score = 10.0 - (e * 10.0)
    return round(max(1, min(10, score)), 2)


def compute_grade(h: float, v: float, edge: float, corner: float) -> float:
    centering_raw = (h + v) / 2
    centering_fixed = 1 - centering_raw

    corner_adj = remap_corner_for_model(corner)

    grade = (
        5.90
        + 3.20 * centering_fixed
        - 0.15 * edge
        + 3.60 * corner_adj
    )

    # Corner caps
    if corner_adj < 0.20:
        grade = min(grade, 7.5)
    elif corner_adj < 0.35:
        grade = min(grade, 8.5)

    # Centering caps
    worst_centering = min(h, v)
    if worst_centering < 0.70:
        grade = min(grade, 8.5)
    if worst_centering < 0.60:
        grade = min(grade, 7.5)

    # Low-grade correction
    if corner_adj < 0.30:
        grade -= 0.8

    if corner_adj < 0.22:
        grade -= 0.5

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

    st.markdown("### Centering")
    st.write("Horizontal Centering:", ratio_to_psa_centering(h))
    st.write("Vertical Centering:", ratio_to_psa_centering(v))
    st.write("Centering Grade:", centering_psa_grade(h, v))

    st.markdown("### Subgrades (Out of 10)")
    st.write("Corners:", corner_subgrade(corner))
    st.write("Edges:", edge_subgrade(edge))


def pil_to_base64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def render_overlay_image(
    img: Image.Image,
    left_x: float,
    right_x: float,
    top_y: float,
    bottom_y: float
) -> None:
    img_b64 = pil_to_base64(img)
    width, height = img.size

    html = f"""
    <div style="
        position: relative;
        width: {width}px;
        height: {height}px;
        margin: 0;
        padding: 0;
        overflow: hidden;
        border: 1px solid #666;
    ">
        <img
            src="data:image/png;base64,{img_b64}"
            style="
                position: absolute;
                top: 0;
                left: 0;
                width: {width}px;
                height: {height}px;
                object-fit: contain;
                z-index: 1;
            "
        />

        <div style="
            position: absolute;
            top: 0;
            left: {left_x}px;
            width: 3px;
            height: {height}px;
            background: #00FF00;
            z-index: 2;
        "></div>

        <div style="
            position: absolute;
            top: 0;
            left: {right_x}px;
            width: 3px;
            height: {height}px;
            background: #00FF00;
            z-index: 2;
        "></div>

        <div style="
            position: absolute;
            top: {top_y}px;
            left: 0;
            width: {width}px;
            height: 3px;
            background: #00FF00;
            z-index: 2;
        "></div>

        <div style="
            position: absolute;
            top: {bottom_y}px;
            left: 0;
            width: {width}px;
            height: 3px;
            background: #00FF00;
            z-index: 2;
        "></div>
    </div>
    """

    components.html(html, height=height + 10, width=width + 10, scrolling=False)

# ============================================================
# MANUAL CENTERING ASSIST
# ============================================================

st.markdown("## Manual Centering Assist")
use_manual_centering = st.checkbox("Use front centering assist")

manual_left = manual_right = manual_top = manual_bottom = None
manual_h_ratio = manual_v_ratio = None

if use_manual_centering:
    if full_card_front is None:
        st.info("Upload a front image to use centering assist.")
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

        st.markdown(
            '<div class="small-note">Move the sliders to place the 4 guide lines directly on the measurable front borders.</div>',
            unsafe_allow_html=True
        )

        col_a, col_b = st.columns([1, 2])

        with col_a:
            left_percent = st.slider("Left Line", 0, 100, 8)
            right_percent = st.slider("Right Line", 0, 100, 92)
            top_percent = st.slider("Top Line", 0, 100, 8)
            bottom_percent = st.slider("Bottom Line", 0, 100, 92)

        left_x = (left_percent / 100.0) * display_width
        right_x = (right_percent / 100.0) * display_width
        top_y = (top_percent / 100.0) * display_height
        bottom_y = (bottom_percent / 100.0) * display_height

        with col_b:
            render_overlay_image(display_image, left_x, right_x, top_y, bottom_y)

        if right_x <= left_x or bottom_y <= top_y:
            st.error("Right line must be right of left line, and bottom line must be below top line.")
        else:
            manual_left = left_x
            manual_right = display_width - right_x
            manual_top = top_y
            manual_bottom = display_height - bottom_y

            manual_h_ratio = safe_ratio(manual_left, manual_right)
            manual_v_ratio = safe_ratio(manual_top, manual_bottom)

            st.write("Manual Horizontal Ratio:", round(manual_h_ratio, 4))
            st.write("Manual Vertical Ratio:", round(manual_v_ratio, 4))
            st.write("Manual Horizontal Centering:", ratio_to_psa_centering(manual_h_ratio))
            st.write("Manual Vertical Centering:", ratio_to_psa_centering(manual_v_ratio))
            st.write("Manual Centering Grade:", centering_psa_grade(manual_h_ratio, manual_v_ratio))

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

    if use_manual_centering and manual_h_ratio is not None and manual_v_ratio is not None:
        h = manual_h_ratio
        v = manual_v_ratio
        st.info("Manual front centering applied")

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

    grade = compute_grade(h, v, edge, corner)

    st.markdown("## Grade")
    st.markdown(f"### {grade}")

    decision_panel(grade, h, v, edge, corner)

    st.markdown("### Raw Feature Values")
    st.write("Horizontal Ratio:", round(h, 4))
    st.write("Vertical Ratio:", round(v, 4))
    st.write("Horizontal Centering:", ratio_to_psa_centering(h))
    st.write("Vertical Centering:", ratio_to_psa_centering(v))
    st.write("Corner Score:", round(corner, 4))
    st.write("Adjusted Corner Score:", round(remap_corner_for_model(corner), 4))
    st.write("Edge Score:", round(edge, 4))

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
