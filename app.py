import base64
import io
import uuid
from datetime import datetime

import numpy as np
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image, ImageDraw

# ============================================================
# DESIGN THEME
# ============================================================

st.set_page_config(page_title="Voodoo Sports Grading", layout="wide")

st.markdown("""
<style>
.stApp {
    background: linear-gradient(90deg, #3F1D6A, #522C87, #5F3A96);
}
html, body, [class*="css"] {
    color: white !important;
}
h1, h2, h3, h4, h5, h6 {
    color: #C9A44D !important;
}
label, p, span, div, .stMarkdown {
    color: white !important;
}
.small-note {
    color: #dddddd !important;
    font-size: 0.85rem;
}
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
div[data-baseweb="select"] * {
    color: black !important;
}
.stButton > button {
    background-color: #C9A44D !important;
    color: black !important;
    border-radius: 10px !important;
    font-weight: bold !important;
}
thead tr th,
tbody tr td {
    color: white !important;
}
[data-testid="stMetricValue"],
[data-testid="stMetricLabel"] {
    color: white !important;
}
[data-testid="stFileUploader"] {
    padding: 0.2rem 0.2rem !important;
}
[data-testid="stFileUploader"] section {
    padding: 0.4rem 0.5rem !important;
    min-height: 40px !important;
}
[data-testid="stFileUploader"] div {
    font-size: 0.78rem !important;
}
.upload-title {
    font-size: 0.9rem;
    margin-bottom: 0.15rem;
}
.preview-card {
    border: 1px solid rgba(255,255,255,0.2);
    border-radius: 10px;
    padding: 0.5rem;
    background: rgba(255,255,255,0.03);
}
.guide-box {
    border: 1px solid rgba(255,255,255,0.22);
    border-radius: 10px;
    padding: 12px;
    background: rgba(255,255,255,0.05);
    margin-bottom: 14px;
}
.guide-title {
    font-weight: 700;
    color: #C9A44D;
    margin-bottom: 8px;
}
.section-box {
    border: 1px solid rgba(255,255,255,0.18);
    border-radius: 12px;
    padding: 12px;
    background: rgba(255,255,255,0.04);
    margin-bottom: 14px;
}
</style>
""", unsafe_allow_html=True)

st.title("VOODOO SPORTS GRADING")

# ============================================================
# CONFIG
# ============================================================

MODEL_VERSION = "v9.7.2"
st.write("RUNNING VERSION:", MODEL_VERSION)

SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
API_BASE = "https://voodoo-centering-api.onrender.com"

TABLE_URL = f"{SUPABASE_URL}/rest/v1/submissions"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}

upload_headers = {
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "apikey": SUPABASE_KEY,
    "Content-Type": "image/jpeg",
}

if "upload_key" not in st.session_state:
    st.session_state.upload_key = str(uuid.uuid4())

if "last_save_success" not in st.session_state:
    st.session_state.last_save_success = False

if "analysis_complete" not in st.session_state:
    st.session_state.analysis_complete = False

if "analysis_payload" not in st.session_state:
    st.session_state.analysis_payload = None

if "analysis_front_bytes" not in st.session_state:
    st.session_state.analysis_front_bytes = None

if "analysis_back_bytes" not in st.session_state:
    st.session_state.analysis_back_bytes = None

if "player_name_edit" not in st.session_state:
    st.session_state.player_name_edit = ""

# ============================================================
# HELPERS
# ============================================================

def json_safe(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, np.bool_):
        return bool(value)
    return value


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
    elif worst >= 0.80:
        return 9.0
    elif worst >= 0.70:
        return 8.0
    else:
        return 7.0


def remap_corner_for_model(corner: float) -> float:
    c = max(0.0, min(1.0, float(corner)))
    return float(np.clip(np.sqrt(c), 0, 1))


def corner_grade_band(corner: float) -> float:
    c = remap_corner_for_model(corner)
    if c >= 0.58:
        return 10.0
    elif c >= 0.51:
        return 9.0
    elif c >= 0.46:
        return 8.0
    elif c >= 0.38:
        return 7.0
    else:
        return 6.0


def edge_grade_band(edge: float) -> float:
    e = max(0.0, min(1.0, float(edge)))
    if e <= 0.006:
        return 10.0
    elif e <= 0.012:
        return 9.0
    elif e <= 0.020:
        return 8.0
    elif e <= 0.032:
        return 7.0
    else:
        return 6.0


def surface_grade_band(surface: float) -> float:
    s = max(0.0, min(1.0, float(surface)))
    if s <= 0.08:
        return 10.0
    elif s <= 0.10:
        return 9.0
    elif s <= 0.13:
        return 8.0
    elif s <= 0.16:
        return 7.0
    else:
        return 6.0


def corner_subgrade(corner: float) -> float:
    return corner_grade_band(corner)


def edge_subgrade(edge: float) -> float:
    return edge_grade_band(edge)


def surface_subgrade(surface: float) -> float:
    return surface_grade_band(surface)


# ============================================================
# GRADE MODEL
# ============================================================

def compute_fitted_grade(
    horizontal_ratio: float,
    vertical_ratio: float,
    corner_score: float,
    edge_score: float,
    surface_score: float
) -> float:
    v_good = 1.0 - float(vertical_ratio)
    corner_bad = float(corner_score)
    edge_bad = float(edge_score)
    surface_bad = float(surface_score)

    grade = (
        8.35
        + 0.25 * v_good
        - 0.47 * corner_bad
        - 0.94 * edge_bad
        + 38.67 * surface_bad
        - 350.94 * (surface_bad ** 2)
    )

    return round(max(1.0, min(10.0, grade)), 2)


def compute_psa_caps(h: float, v: float, edge: float, corner: float, surface: float) -> dict:
    centering_cap = centering_psa_grade(h, v)
    corner_cap = corner_grade_band(corner)
    edge_cap = edge_grade_band(edge)
    surface_cap = surface_grade_band(surface)

    overall = compute_fitted_grade(h, v, corner, edge, surface)

    cap_values = {
        "Centering": centering_cap,
        "Corners": corner_cap,
        "Edges": edge_cap,
        "Surface": surface_cap,
    }
    limiting_feature = min(cap_values, key=cap_values.get)

    return {
        "overall_grade": overall,
        "candidate_grade": overall,
        "base_fitted_grade": overall,
        "centering_cap": round(centering_cap, 2),
        "corner_cap": round(corner_cap, 2),
        "edge_cap": round(edge_cap, 2),
        "surface_cap": round(surface_cap, 2),
        "weakest_cap": round(min(cap_values.values()), 2),
        "limiter": limiting_feature,
        "centering_strength": round(centering_cap / 10.0, 3),
        "corner_strength": round(corner_cap / 10.0, 3),
        "edge_strength": round(edge_cap / 10.0, 3),
        "surface_strength": round(surface_cap / 10.0, 3),
    }


def compute_grade(h: float, v: float, edge: float, corner: float, surface: float) -> float:
    return compute_fitted_grade(h, v, corner, edge, surface)


# ============================================================
# CONFIDENCE LAYER (KEEP V9.7.1)
# ============================================================

def band_distance_centering(h: float, v: float) -> float:
    worst = min(float(h), float(v))
    thresholds = [0.70, 0.80, 0.90]
    return min(abs(worst - t) for t in thresholds)


def band_distance_corner(corner: float) -> float:
    c = remap_corner_for_model(corner)
    thresholds = [0.38, 0.46, 0.51, 0.58]
    return min(abs(c - t) for t in thresholds)


def band_distance_edge(edge: float) -> float:
    e = max(0.0, min(1.0, float(edge)))
    thresholds = [0.006, 0.012, 0.020, 0.032]
    return min(abs(e - t) for t in thresholds)


def band_distance_surface(surface: float) -> float:
    s = max(0.0, min(1.0, float(surface)))
    thresholds = [0.08, 0.10, 0.13, 0.16]
    return min(abs(s - t) for t in thresholds)


def compute_confidence(
    h: float,
    v: float,
    edge: float,
    corner: float,
    surface: float,
    used_surface_fallback: bool = False,
    corner_count: int = 0
) -> dict:
    centering_band = centering_psa_grade(h, v)
    corner_band = corner_grade_band(corner)
    edge_band = edge_grade_band(edge)
    surface_band = surface_grade_band(surface)

    bands = [centering_band, corner_band, edge_band, surface_band]

    spread = max(bands) - min(bands)
    agreement_score = max(0.0, 1.0 - (spread / 6.0))

    d_center = band_distance_centering(h, v)
    d_corner = band_distance_corner(corner)
    d_edge = band_distance_edge(edge)
    d_surface = band_distance_surface(surface)

    center_conf = min(1.0, d_center / 0.085)
    corner_conf = min(1.0, d_corner / 0.14)
    edge_conf = min(1.0, d_edge / 0.020)
    surface_conf = min(1.0, d_surface / 0.055)

    threshold_score = (center_conf + corner_conf + edge_conf + surface_conf) / 4.0

    data_score = 1.0
    if used_surface_fallback:
        data_score -= 0.12
    if corner_count < 2:
        data_score -= 0.20
    elif corner_count == 2:
        data_score -= 0.03

    data_score = max(0.0, min(1.0, data_score))

    confidence_raw = (
        0.50 * agreement_score +
        0.30 * threshold_score +
        0.20 * data_score
    )

    confidence_raw = max(0.0, min(1.0, confidence_raw))

    confidence_percent = round(confidence_raw * 100.0, 1)

    if confidence_percent >= 75:
        label = "High"
    elif confidence_percent >= 55:
        label = "Moderate"
    else:
        label = "Low"

    return {
        "confidence_score": round(confidence_raw, 3),
        "confidence_percent": confidence_percent,
        "confidence_label": label,
        "agreement_score": round(agreement_score, 3),
        "threshold_score": round(threshold_score, 3),
        "data_score": round(data_score, 3),
        "band_spread": round(spread, 2),
        "centering_band": centering_band,
        "corner_band": corner_band,
        "edge_band": edge_band,
        "surface_band": surface_band,
    }


# ============================================================
# SUBMIT RECOMMENDATION RULES (KEEP CURRENT)
# ============================================================

def compute_submit_probability(
    grade: float,
    confidence_score: float,
    surface: float,
    band_spread: float
) -> dict:
    confidence_percent = confidence_score * 100.0

    if grade >= 9.4:
        label = "Strong Submit"
        probability = 0.95
    elif grade >= 9.0:
        label = "Submit"
        probability = 0.82
    elif 8.6 <= grade < 9.0 and confidence_percent >= 58.0:
        label = "Risky"
        probability = 0.58
    else:
        label = "Do Not Submit"
        probability = 0.15

    return {
        "submit_probability": round(probability, 3),
        "submit_percent": round(probability * 100, 1),
        "submit_label": label,
    }


# ============================================================
# PLAYER NAME DETECTION
# ============================================================

def detect_player_name(front_bytes: bytes) -> dict:
    try:
        resp = requests.post(
            f"{API_BASE}/extract_card_metadata",
            files={"file": ("front.jpg", front_bytes, "image/jpeg")},
            timeout=60,
        )

        if resp.status_code != 200:
            return {
                "player_name": None,
                "player_name_confidence": None,
                "player_name_source": "unavailable",
            }

        data = resp.json()
        if "error" in data:
            return {
                "player_name": None,
                "player_name_confidence": None,
                "player_name_source": "error",
            }

        return {
            "player_name": data.get("player_name"),
            "player_name_confidence": data.get("player_name_confidence"),
            "player_name_source": data.get("player_name_source", "vision"),
        }
    except Exception:
        return {
            "player_name": None,
            "player_name_confidence": None,
            "player_name_source": "unavailable",
        }


# ============================================================
# UI HELPERS
# ============================================================

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
        border-radius: 8px;
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
        <div style="position:absolute;top:0;left:{left_x}px;width:2px;height:{height}px;background:#00FF00;z-index:2;"></div>
        <div style="position:absolute;top:0;left:{right_x}px;width:2px;height:{height}px;background:#00FF00;z-index:2;"></div>
        <div style="position:absolute;top:{top_y}px;left:0;width:{width}px;height:2px;background:#00FF00;z-index:2;"></div>
        <div style="position:absolute;top:{bottom_y}px;left:0;width:{width}px;height:2px;background:#00FF00;z-index:2;"></div>
    </div>
    """
    components.html(html, height=height + 8, width=width + 8, scrolling=False)


def build_card_preview_with_overlay(
    image_bytes: bytes,
    horizontal_ratio: float = None,
    vertical_ratio: float = None,
    max_width: int = 320
):
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception:
        return None

    scale = min(1.0, max_width / img.width)
    new_size = (int(img.width * scale), int(img.height * scale))
    preview = img.resize(new_size)
    draw = ImageDraw.Draw(preview)

    w, h = preview.size

    if horizontal_ratio is not None and 0 < float(horizontal_ratio) <= 1:
        r = float(horizontal_ratio)
        left_prop = r / (1 + r)
        right_prop = 1 / (1 + r)
        left_x = int(w * left_prop)
        right_x = int(w * right_prop)
        draw.line([(left_x, 0), (left_x, h)], fill=(0, 255, 0), width=2)
        draw.line([(right_x, 0), (right_x, h)], fill=(0, 255, 0), width=2)

    if vertical_ratio is not None and 0 < float(vertical_ratio) <= 1:
        r = float(vertical_ratio)
        top_prop = r / (1 + r)
        bottom_prop = 1 / (1 + r)
        top_y = int(h * top_prop)
        bottom_y = int(h * bottom_prop)
        draw.line([(0, top_y), (w, top_y)], fill=(0, 255, 0), width=2)
        draw.line([(0, bottom_y), (w, bottom_y)], fill=(0, 255, 0), width=2)

    return preview


def backfill_surface_from_url(front_image_url: str):
    if not front_image_url:
        return None, None, None, None

    try:
        img_resp = requests.get(front_image_url, timeout=60)
        if img_resp.status_code != 200:
            return None, None, None, None

        sr = requests.post(
            f"{API_BASE}/analyze_surface",
            files={"file": ("front.jpg", img_resp.content, "image/jpeg")},
            timeout=60,
        )

        if sr.status_code != 200:
            return None, None, None, None

        surface_data = sr.json()
        if "error" in surface_data:
            return None, None, None, None

        return (
            surface_data.get("surface_score"),
            surface_data.get("scratch_score"),
            surface_data.get("speckle_score"),
            surface_data.get("gloss_score"),
        )
    except Exception:
        return None, None, None, None


def decision_panel_admin(
    grade: float,
    h: float,
    v: float,
    edge: float,
    corner: float,
    surface: float,
    confidence: dict,
    submit: dict
) -> None:
    caps = compute_psa_caps(h, v, edge, corner, surface)

    if submit["submit_label"] == "Strong Submit":
        st.success("STRONG SUBMIT")
    elif submit["submit_label"] == "Submit":
        st.success("SUBMIT")
    elif submit["submit_label"] == "Risky":
        st.warning("RISKY")
    else:
        st.error("DO NOT SUBMIT")

    st.markdown("### Submission Decision")
    st.write("Submit Probability:", f"{submit['submit_percent']:.1f}%")
    st.write("Recommendation:", submit["submit_label"])

    st.markdown("### Confidence")
    st.write("Confidence Score:", f"{confidence['confidence_percent']:.1f}%")
    st.write("Confidence Level:", confidence["confidence_label"])
    st.write(
        "Risk Level:",
        "Low" if confidence["confidence_score"] >= 0.75 else
        "Moderate" if confidence["confidence_score"] >= 0.55 else
        "High"
    )
    st.write("Limiting Feature:", caps["limiter"])

    st.markdown("### Centering")
    st.write("Horizontal Centering:", ratio_to_psa_centering(h))
    st.write("Vertical Centering:", ratio_to_psa_centering(v))
    st.write("Centering Grade:", centering_psa_grade(h, v))

    st.markdown("### Subgrades (Out of 10)")
    st.write("Corners:", corner_subgrade(corner))
    st.write("Edges:", edge_subgrade(edge))
    st.write("Surface:", surface_subgrade(surface))

    st.markdown("### Confidence Breakdown")
    st.write("Agreement Score:", confidence["agreement_score"])
    st.write("Threshold Score:", confidence["threshold_score"])
    st.write("Data Quality Score:", confidence["data_score"])
    st.write("Band Spread:", confidence["band_spread"])

    st.markdown("### Fitted Formula Output")
    st.write("Base Fitted Grade:", caps["base_fitted_grade"])
    st.write("Predicted Grade:", caps["candidate_grade"])
    st.write("Centering Band:", caps["centering_cap"])
    st.write("Corner Band:", caps["corner_cap"])
    st.write("Edge Band:", caps["edge_cap"])
    st.write("Surface Band:", caps["surface_cap"])


def decision_panel_user(
    grade: float,
    h: float,
    v: float,
    corner: float,
    edge: float,
    surface: float,
    confidence: dict,
    submit: dict
) -> None:
    if submit["submit_label"] == "Strong Submit":
        st.success("STRONG SUBMIT")
    elif submit["submit_label"] == "Submit":
        st.success("SUBMIT")
    elif submit["submit_label"] == "Risky":
        st.warning("RISKY")
    else:
        st.error("DO NOT SUBMIT")

    st.markdown("## Result")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Grade", grade)

    with col2:
        st.metric("Confidence", f"{confidence['confidence_percent']:.1f}%")

    with col3:
        st.metric("Submit", submit["submit_label"])

    st.markdown("### Centering")
    st.write("Horizontal:", ratio_to_psa_centering(h))
    st.write("Vertical:", ratio_to_psa_centering(v))

    st.markdown("### Subgrades")
    st.write("Corners:", corner_subgrade(corner))
    st.write("Edges:", edge_subgrade(edge))
    st.write("Surface:", surface_subgrade(surface))


def reset_analysis_state():
    st.session_state.analysis_complete = False
    st.session_state.analysis_payload = None
    st.session_state.analysis_front_bytes = None
    st.session_state.analysis_back_bytes = None
    st.session_state.player_name_edit = ""
    st.session_state.last_save_success = False


# ============================================================
# ACCESS + USER GUIDE
# ============================================================

st.markdown("### Access")
user_email = st.text_input("Enter Access Email")

st.markdown("""
<div class="guide-box">
    <div class="guide-title">USER GUIDE BEST PRACTICES:</div>
    <div>• All pictures taken from same height/zoom with similar lighting</div>
    <div>• Take pictures of all 4 front corners</div>
    <div>• Use manual centering</div>
</div>
""", unsafe_allow_html=True)

if user_email:
    user_check = requests.get(
        f"{SUPABASE_URL}/rest/v1/authorized_users?email=eq.{user_email}",
        headers=headers,
        timeout=30,
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
stock_type = st.selectbox("Stock Type", ["paper", "chrome", "refractor", "foil", "other"])

psa_is_graded = st.checkbox("PSA graded?")
psa_actual_grade = None
if psa_is_graded:
    psa_actual_grade = st.number_input("PSA Grade", 1.0, 10.0, step=0.5)

# ============================================================
# IMAGE INPUTS
# ============================================================

st.markdown("## Upload Card Images")

clear_col, _ = st.columns([1, 3])
with clear_col:
    if st.button("🧹 Clear Images"):
        st.session_state.upload_key = str(uuid.uuid4())
        reset_analysis_state()
        st.rerun()

st.markdown('<div class="upload-title">Front Image</div>', unsafe_allow_html=True)
full_card_front = st.file_uploader(
    "",
    ["jpg", "jpeg", "png"],
    key=f"front_{st.session_state.upload_key}",
    label_visibility="collapsed"
)

st.markdown('<div class="upload-title">Back Image</div>', unsafe_allow_html=True)
full_card_back = st.file_uploader(
    "",
    ["jpg", "jpeg", "png"],
    key=f"back_{st.session_state.upload_key}",
    label_visibility="collapsed"
)

st.markdown("### Corner Images (2 Required)")
st.markdown('<div class="upload-title">Corner 1</div>', unsafe_allow_html=True)
corner1 = st.file_uploader(
    "",
    ["jpg", "jpeg", "png"],
    key=f"c1_{st.session_state.upload_key}",
    label_visibility="collapsed"
)

st.markdown('<div class="upload-title">Corner 2</div>', unsafe_allow_html=True)
corner2 = st.file_uploader(
    "",
    ["jpg", "jpeg", "png"],
    key=f"c2_{st.session_state.upload_key}",
    label_visibility="collapsed"
)

st.markdown('<div class="upload-title">Corner 3 (Optional)</div>', unsafe_allow_html=True)
corner3 = st.file_uploader(
    "",
    ["jpg", "jpeg", "png"],
    key=f"c3_{st.session_state.upload_key}",
    label_visibility="collapsed"
)

st.markdown('<div class="upload-title">Corner 4 (Optional)</div>', unsafe_allow_html=True)
corner4 = st.file_uploader(
    "",
    ["jpg", "jpeg", "png"],
    key=f"c4_{st.session_state.upload_key}",
    label_visibility="collapsed"
)

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
            front_image = front_image.transpose(Image.Transpose.ROTATE_270)
        except Exception as e:
            st.error(f"Could not open front image: {e}")
            st.stop()

        max_display_width = 450
        scale = min(1.0, max_display_width / front_image.width)
        display_width = int(front_image.width * scale)
        display_height = int(front_image.height * scale)
        display_image = front_image.resize((display_width, display_height))

        st.markdown(
            '<div class="small-note">Image rotated 90 degrees clockwise for manual centering. Use fine sliders for precise mobile adjustment.</div>',
            unsafe_allow_html=True
        )

        col_a, col_b = st.columns([1, 1.1])

        with col_a:
            left_percent = st.slider("Left", 0.0, 100.0, 8.0, step=0.1)
            right_percent = st.slider("Right", 0.0, 100.0, 92.0, step=0.1)
            top_percent = st.slider("Top", 0.0, 100.0, 8.0, step=0.1)
            bottom_percent = st.slider("Bottom", 0.0, 100.0, 92.0, step=0.1)

        left_x = (left_percent / 100.0) * display_width
        right_x = (right_percent / 100.0) * display_width
        top_y = (top_percent / 100.0) * display_height
        bottom_y = (bottom_percent / 100.0) * display_height

        with col_b:
            render_overlay_image(display_image, left_x, right_x, top_y, bottom_y)

        if right_x <= left_x or bottom_y <= top_y:
            st.error("Right must be right of left, and bottom must be below top.")
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
    st.session_state.last_save_success = False
    reset_analysis_state()

    if full_card_front is None:
        st.error("Front image required")
        st.stop()

    if full_card_back is None:
        st.error("Back image required")
        st.stop()

    if corner1 is None or corner2 is None:
        st.error("At least 2 corner images are required")
        st.stop()

    front_bytes = full_card_front.getvalue()
    back_bytes = full_card_back.getvalue()

    try:
        r = requests.post(
            f"{API_BASE}/analyze",
            files={"file": ("front.jpg", front_bytes, "image/jpeg")},
            timeout=60,
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

    corner_scores = []
    for c in corner_files:
        try:
            cr = requests.post(
                f"{API_BASE}/analyze_corner",
                files={"file": ("corner.jpg", c.getvalue(), "image/jpeg")},
                timeout=60,
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

        corner_scores.append(corner_data["corner_score"])

    if len(corner_scores) == 0:
        corner = 0.5
        st.warning("All corner analyses failed. Using neutral corner score.")
    else:
        corner = min(corner_scores)

    surface = None
    scratch_score = None
    speckle_score = None
    gloss_score = None
    surface_data = None
    used_surface_fallback = False

    try:
        sr = requests.post(
            f"{API_BASE}/analyze_surface",
            files={"file": ("front.jpg", front_bytes, "image/jpeg")},
            timeout=60,
        )
    except Exception as e:
        st.warning(f"Surface API request failed: {e}")
        sr = None

    if sr is not None and sr.status_code == 200:
        try:
            surface_data = sr.json()
        except Exception:
            surface_data = {"error": f"Surface API returned invalid JSON: {sr.text}"}

        if "error" in surface_data:
            st.warning(f"Surface API error: {surface_data['error']}")
        else:
            surface = surface_data.get("surface_score")
            scratch_score = surface_data.get("scratch_score")
            speckle_score = surface_data.get("speckle_score")
            gloss_score = surface_data.get("gloss_score")
    elif sr is not None:
        st.warning(f"Surface API failed: {sr.text}")

    if surface is None:
        surface = 0.12
        used_surface_fallback = True
        st.warning("Surface model not applied. Using fallback surface score of 0.12.")

    player_meta = detect_player_name(front_bytes)
    detected_player_name = player_meta.get("player_name")
    detected_player_confidence = player_meta.get("player_name_confidence")
    detected_player_source = player_meta.get("player_name_source")

    st.session_state.player_name_edit = detected_player_name if detected_player_name else ""

    grade = compute_grade(h, v, edge, corner, float(surface))
    base_grade = compute_fitted_grade(h, v, corner, edge, float(surface))

    confidence = compute_confidence(
        h=h,
        v=v,
        edge=edge,
        corner=corner,
        surface=float(surface),
        used_surface_fallback=used_surface_fallback,
        corner_count=len(corner_scores),
    )

    submit = compute_submit_probability(
        grade=grade,
        confidence_score=confidence["confidence_score"],
        surface=float(surface),
        band_spread=confidence["band_spread"],
    )

    preview_img = build_card_preview_with_overlay(
        image_bytes=front_bytes,
        horizontal_ratio=h,
        vertical_ratio=v,
        max_width=320
    )

    st.session_state.analysis_payload = {
        "manufacturer": manufacturer,
        "stock_type": stock_type,
        "psa_is_graded": psa_is_graded,
        "psa_actual_grade": psa_actual_grade,
        "use_manual_centering": use_manual_centering,
        "manual_left": manual_left,
        "manual_right": manual_right,
        "manual_top": manual_top,
        "manual_bottom": manual_bottom,
        "manual_h_ratio": manual_h_ratio,
        "manual_v_ratio": manual_v_ratio,
        "horizontal_ratio": h,
        "vertical_ratio": v,
        "edge_score": edge,
        "corner_score": corner,
        "surface_score": float(surface),
        "scratch_score": scratch_score,
        "speckle_score": speckle_score,
        "gloss_score": gloss_score,
        "surface_data": surface_data,
        "used_surface_fallback": used_surface_fallback,
        "base_fitted_grade": base_grade,
        "grade": grade,
        "confidence": confidence,
        "submit": submit,
        "preview_img": preview_img,
        "detected_player_name": detected_player_name,
        "detected_player_confidence": detected_player_confidence,
        "detected_player_source": detected_player_source,
        "corner_count": len(corner_scores),
    }
    st.session_state.analysis_front_bytes = front_bytes
    st.session_state.analysis_back_bytes = back_bytes
    st.session_state.analysis_complete = True

# ============================================================
# RESULTS / SAVE
# ============================================================

if st.session_state.analysis_complete and st.session_state.analysis_payload is not None:
    result = st.session_state.analysis_payload

    detected_player_name = result["detected_player_name"]
    detected_player_confidence = result["detected_player_confidence"]
    detected_player_source = result["detected_player_source"]

    st.markdown("### Player Name")
    if detected_player_name:
        msg = f"Detected player: {detected_player_name}"
        if detected_player_confidence is not None:
            msg += f" ({round(float(detected_player_confidence) * 100, 1)}%)"
        st.write(msg)
    else:
        st.write("Detected player: Not found")

    st.text_input(
        "Player Name (edit or confirm before save)",
        key="player_name_edit"
    )

    final_player_name = st.session_state.player_name_edit.strip() if st.session_state.player_name_edit else None
    final_player_name_confidence = detected_player_confidence if detected_player_name else None

    if final_player_name and final_player_name != detected_player_name:
        final_player_name_source = "manual_override"
    else:
        final_player_name_source = detected_player_source

    if result["preview_img"] is not None:
        st.markdown("### Card Preview")
        st.markdown('<div class="preview-card">', unsafe_allow_html=True)
        st.image(result["preview_img"], caption="Preview with centering overlay lines", use_container_width=False)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("## Grade")
    st.markdown(f"### {result['grade']}")

    if user_role == "admin":
        decision_panel_admin(
            result["grade"],
            result["horizontal_ratio"],
            result["vertical_ratio"],
            result["edge_score"],
            result["corner_score"],
            result["surface_score"],
            result["confidence"],
            result["submit"],
        )
    else:
        decision_panel_user(
            result["grade"],
            result["horizontal_ratio"],
            result["vertical_ratio"],
            result["corner_score"],
            result["edge_score"],
            result["surface_score"],
            result["confidence"],
            result["submit"],
        )

    if user_role == "admin":
        st.markdown("### Raw Feature Values")
        st.write("Horizontal Ratio:", round(result["horizontal_ratio"], 4))
        st.write("Vertical Ratio:", round(result["vertical_ratio"], 4))
        st.write("Horizontal Centering:", ratio_to_psa_centering(result["horizontal_ratio"]))
        st.write("Vertical Centering:", ratio_to_psa_centering(result["vertical_ratio"]))
        st.write("Corner Score:", round(result["corner_score"], 4))
        st.write("Adjusted Corner Score:", round(remap_corner_for_model(result["corner_score"]), 4))
        st.write("Edge Score:", round(result["edge_score"], 4))
        st.write("Surface Score:", round(float(result["surface_score"]), 4))
        st.write("Base Fitted Grade:", round(float(result["base_fitted_grade"]), 2))
        if result["scratch_score"] is not None:
            st.write("Scratch Score:", round(float(result["scratch_score"]), 4))
        if result["speckle_score"] is not None:
            st.write("Speckle Score:", round(float(result["speckle_score"]), 4))
        if result["gloss_score"] is not None:
            st.write("Gloss Score:", round(float(result["gloss_score"]), 4))

    if st.button("Save Submission"):
        front_bytes = st.session_state.analysis_front_bytes
        back_bytes = st.session_state.analysis_back_bytes

        if front_bytes is None:
            st.error("Missing analyzed front image bytes.")
            st.stop()

        card_id = str(uuid.uuid4())
        front_name = f"{card_id}_front.jpg"
        back_name = f"{card_id}_back.jpg"

        front_upload = requests.post(
            f"{SUPABASE_URL}/storage/v1/object/card-images/{front_name}",
            headers=upload_headers,
            data=front_bytes,
            timeout=60,
        )
        if front_upload.status_code not in [200, 201]:
            st.error(f"Front upload failed: {front_upload.text}")
            st.stop()

        if back_bytes is not None:
            back_upload = requests.post(
                f"{SUPABASE_URL}/storage/v1/object/card-images/{back_name}",
                headers=upload_headers,
                data=back_bytes,
                timeout=60,
            )
            if back_upload.status_code not in [200, 201]:
                st.error(f"Back upload failed: {back_upload.text}")
                st.stop()

        front_url = f"{SUPABASE_URL}/storage/v1/object/public/card-images/{front_name}"
        back_url = f"{SUPABASE_URL}/storage/v1/object/public/card-images/{back_name}" if back_bytes else None

        payload = {
            "card_id": card_id,
            "model_version": MODEL_VERSION,
            "manufacturer": json_safe(manufacturer),
            "stock_type": json_safe(stock_type),
            "psa_is_graded": json_safe(psa_is_graded),
            "psa_actual_grade": json_safe(psa_actual_grade),
            "player_name": json_safe(final_player_name),
            "player_name_confidence": json_safe(final_player_name_confidence),
            "player_name_source": json_safe(final_player_name_source),
            "horizontal_ratio": json_safe(result["horizontal_ratio"]),
            "vertical_ratio": json_safe(result["vertical_ratio"]),
            "edge_score": json_safe(result["edge_score"]),
            "corner_score": json_safe(result["corner_score"]),
            "surface_score": json_safe(result["surface_score"]),
            "scratch_score": json_safe(result["scratch_score"]),
            "speckle_score": json_safe(result["speckle_score"]),
            "gloss_score": json_safe(result["gloss_score"]),
            "calibrated_grade": json_safe(result["grade"]),
            "confidence_score": json_safe(result["confidence"]["confidence_score"]),
            "confidence_percent": json_safe(result["confidence"]["confidence_percent"]),
            "confidence_label": json_safe(result["confidence"]["confidence_label"]),
            "agreement_score": json_safe(result["confidence"]["agreement_score"]),
            "threshold_score": json_safe(result["confidence"]["threshold_score"]),
            "data_score": json_safe(result["confidence"]["data_score"]),
            "band_spread": json_safe(result["confidence"]["band_spread"]),
            "submit_probability": json_safe(result["submit"]["submit_probability"]),
            "submit_percent": json_safe(result["submit"]["submit_percent"]),
            "submit_label": json_safe(result["submit"]["submit_label"]),
            "front_image_url": json_safe(front_url),
            "back_image_url": json_safe(back_url),
            "submitted_by": user_email,
            "created_at": str(datetime.now()),
            "manual_centering_used": json_safe(result["use_manual_centering"]),
            "front_left_measurement": json_safe(result["manual_left"] if result["use_manual_centering"] else None),
            "front_right_measurement": json_safe(result["manual_right"] if result["use_manual_centering"] else None),
            "front_top_measurement": json_safe(result["manual_top"] if result["use_manual_centering"] else None),
            "front_bottom_measurement": json_safe(result["manual_bottom"] if result["use_manual_centering"] else None),
            "front_horizontal_ratio_manual": json_safe(result["manual_h_ratio"] if result["use_manual_centering"] else None),
            "front_vertical_ratio_manual": json_safe(result["manual_v_ratio"] if result["use_manual_centering"] else None),
        }

        if user_role == "admin":
            with st.expander("Debug"):
                st.write("DEBUG surface response:", result["surface_data"] if result["surface_data"] is not None else "no surface_data")
                st.write("DEBUG surface final:", result["surface_score"])
                st.write("DEBUG detected player:", detected_player_name)
                st.write("DEBUG player source:", detected_player_source)
                st.write("DEBUG payload player_name:", payload["player_name"])
                st.write("DEBUG payload confidence_percent:", payload["confidence_percent"])
                st.write("DEBUG payload submit_percent:", payload["submit_percent"])
                st.write("DEBUG payload submit_label:", payload["submit_label"])
                st.write("DEBUG payload grade:", payload["calibrated_grade"])

        save_response = requests.post(TABLE_URL, json=payload, headers=headers, timeout=30)

        if save_response.status_code in [200, 201]:
            st.session_state.last_save_success = True
            st.success("Saved successfully")
            st.info("Images remain loaded. Use the 'Clear Images' button when you're ready.")
        else:
            st.session_state.last_save_success = False
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
        progress = st.progress(0)
        status_box = st.empty()
        total_rows = len(df)

        for idx, (_, row) in enumerate(df.iterrows(), start=1):
            if pd.isna(row.get("horizontal_ratio")) or pd.isna(row.get("vertical_ratio")):
                progress.progress(idx / max(total_rows, 1))
                continue

            row_surface = row.get("surface_score")
            row_scratch = row.get("scratch_score")
            row_speckle = row.get("speckle_score")
            row_gloss = row.get("gloss_score")

            if pd.isna(row_surface):
                fetched_surface, fetched_scratch, fetched_speckle, fetched_gloss = backfill_surface_from_url(
                    row.get("front_image_url")
                )
                if fetched_surface is not None:
                    row_surface = fetched_surface
                    row_scratch = fetched_scratch
                    row_speckle = fetched_speckle
                    row_gloss = fetched_gloss

            used_surface_fallback = False
            calc_surface = row_surface
            if pd.isna(calc_surface):
                calc_surface = 0.12
                used_surface_fallback = True

            new_grade = compute_grade(
                float(row["horizontal_ratio"]),
                float(row["vertical_ratio"]),
                float(row["edge_score"]),
                float(row["corner_score"]),
                float(calc_surface),
            )

            confidence = compute_confidence(
                h=float(row["horizontal_ratio"]),
                v=float(row["vertical_ratio"]),
                edge=float(row["edge_score"]),
                corner=float(row["corner_score"]),
                surface=float(calc_surface),
                used_surface_fallback=used_surface_fallback,
                corner_count=2,
            )

            submit = compute_submit_probability(
                grade=new_grade,
                confidence_score=confidence["confidence_score"],
                surface=float(calc_surface),
                band_spread=confidence["band_spread"],
            )

            new_card_id = str(uuid.uuid4())

            new_data = {
                "card_id": new_card_id,
                "model_version": MODEL_VERSION,
                "manufacturer": json_safe(row.get("manufacturer")),
                "stock_type": json_safe(row.get("stock_type")),
                "psa_is_graded": json_safe(row.get("psa_is_graded")),
                "psa_actual_grade": json_safe(row.get("psa_actual_grade")),
                "player_name": json_safe(row.get("player_name")),
                "player_name_confidence": json_safe(row.get("player_name_confidence")),
                "player_name_source": json_safe(row.get("player_name_source")),
                "horizontal_ratio": json_safe(row.get("horizontal_ratio")),
                "vertical_ratio": json_safe(row.get("vertical_ratio")),
                "edge_score": json_safe(row.get("edge_score")),
                "corner_score": json_safe(row.get("corner_score")),
                "surface_score": json_safe(row_surface),
                "scratch_score": json_safe(row_scratch),
                "speckle_score": json_safe(row_speckle),
                "gloss_score": json_safe(row_gloss),
                "calibrated_grade": json_safe(new_grade),
                "confidence_score": json_safe(confidence["confidence_score"]),
                "confidence_percent": json_safe(confidence["confidence_percent"]),
                "confidence_label": json_safe(confidence["confidence_label"]),
                "agreement_score": json_safe(confidence["agreement_score"]),
                "threshold_score": json_safe(confidence["threshold_score"]),
                "data_score": json_safe(confidence["data_score"]),
                "band_spread": json_safe(confidence["band_spread"]),
                "submit_probability": json_safe(submit["submit_probability"]),
                "submit_percent": json_safe(submit["submit_percent"]),
                "submit_label": json_safe(submit["submit_label"]),
                "front_image_url": json_safe(row.get("front_image_url")),
                "back_image_url": json_safe(row.get("back_image_url")),
                "submitted_by": user_email,
                "created_at": str(datetime.now()),
                "manual_centering_used": json_safe(row.get("manual_centering_used")),
                "front_left_measurement": json_safe(row.get("front_left_measurement")),
                "front_right_measurement": json_safe(row.get("front_right_measurement")),
                "front_top_measurement": json_safe(row.get("front_top_measurement")),
                "front_bottom_measurement": json_safe(row.get("front_bottom_measurement")),
                "front_horizontal_ratio_manual": json_safe(row.get("front_horizontal_ratio_manual")),
                "front_vertical_ratio_manual": json_safe(row.get("front_vertical_ratio_manual")),
            }

            try:
                post_resp = requests.post(TABLE_URL, json=new_data, headers=headers, timeout=30)
                if post_resp.status_code not in [200, 201]:
                    status_box.warning(f"Post failed for source card_id {row.get('card_id')}: {post_resp.text}")
            except Exception as e:
                status_box.warning(f"Post exception for source card_id {row.get('card_id')}: {e}")

            status_box.write(
                f"Processed {idx}/{total_rows} | source_card_id={row.get('card_id')} | "
                f"new_card_id={new_card_id} | grade={new_grade} | "
                f"confidence={confidence['confidence_percent']:.1f}% | "
                f"submit={submit['submit_percent']:.1f}% ({submit['submit_label']})"
            )
            progress.progress(idx / max(total_rows, 1))

        st.success("Re-scored and created new submissions.")
