import base64
import csv
import hashlib
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
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Voodoo Sports Grading",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================================
# PREMIUM UI THEME
# ============================================================

st.markdown("""
<style>
:root {
    --bg-1: #3F1D6A;
    --bg-2: #522C87;
    --bg-3: #5F3A96;
    --accent: #C9A44D;
    --accent-soft: rgba(201,164,77,0.16);
    --text: #F8F6FC;
    --muted: #D8D1E6;
    --card: rgba(255,255,255,0.06);
    --card-strong: rgba(255,255,255,0.08);
    --border: rgba(255,255,255,0.14);
    --border-strong: rgba(201,164,77,0.32);
    --shadow: 0 10px 30px rgba(10, 8, 20, 0.28);
    --radius-xl: 20px;
    --radius-lg: 16px;
    --radius-md: 12px;
}

.stApp {
    background:
        radial-gradient(circle at top left, rgba(255,255,255,0.06), transparent 28%),
        linear-gradient(90deg, var(--bg-1), var(--bg-2), var(--bg-3));
}

html, body, [class*="css"] {
    color: var(--text) !important;
}

.block-container {
    max-width: 1220px;
    padding-top: 1.8rem;
    padding-bottom: 2.5rem;
}

h1, h2, h3, h4, h5, h6 {
    color: var(--accent) !important;
    letter-spacing: 0.02em;
}

p, span, div, label, .stMarkdown {
    color: var(--text) !important;
}

small, .small-note {
    color: var(--muted) !important;
    font-size: 0.85rem;
}

[data-testid="stHeader"] {
    background: transparent;
}

input, textarea {
    color: #111 !important;
    -webkit-text-fill-color: #111 !important;
    background-color: #fff !important;
    border-radius: 12px !important;
}
input::placeholder, textarea::placeholder {
    color: #555 !important;
    -webkit-text-fill-color: #555 !important;
}
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stTextArea"] textarea {
    color: #111 !important;
    -webkit-text-fill-color: #111 !important;
    background-color: #fff !important;
    border: 1px solid rgba(0,0,0,0.08) !important;
    min-height: 42px !important;
}

div[data-baseweb="select"] > div {
    border-radius: 12px !important;
    background: #fff !important;
    color: #111 !important;
    border: 1px solid rgba(0,0,0,0.08) !important;
    min-height: 42px !important;
}
div[data-baseweb="select"] * {
    color: #111 !important;
}

[data-baseweb="radio"] label {
    background: rgba(255,255,255,0.05);
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 8px 12px;
    margin-right: 8px;
}

.stButton > button,
[data-testid="stDownloadButton"] > button {
    background: linear-gradient(180deg, #D8B866, #C9A44D) !important;
    color: #1A1621 !important;
    border-radius: 999px !important;
    font-weight: 700 !important;
    border: none !important;
    min-height: 42px !important;
    padding: 0 18px !important;
    box-shadow: 0 10px 20px rgba(0,0,0,0.16);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.stButton > button:hover,
[data-testid="stDownloadButton"] > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 14px 24px rgba(0,0,0,0.22);
}

thead tr th,
tbody tr td {
    color: var(--text) !important;
}
[data-testid="stMetricValue"],
[data-testid="stMetricLabel"] {
    color: var(--text) !important;
}
[data-testid="stMetric"] {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 12px 14px;
    box-shadow: var(--shadow);
}

[data-testid="stFileUploader"] {
    padding: 0.1rem 0.1rem !important;
}
[data-testid="stFileUploader"] section {
    padding: 0.35rem 0.5rem !important;
    min-height: 34px !important;
    border-radius: 14px !important;
    background: rgba(255,255,255,0.04) !important;
    border: 1px dashed rgba(255,255,255,0.22) !important;
}
[data-testid="stFileUploader"] div {
    font-size: 0.78rem !important;
}

hr {
    border-color: rgba(255,255,255,0.12) !important;
}

.premium-shell {
    border: 1px solid rgba(255,255,255,0.08);
    background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.03));
    border-radius: 24px;
    padding: 22px 24px;
    box-shadow: var(--shadow);
    margin-bottom: 18px;
    backdrop-filter: blur(8px);
}

.hero-wrap {
    border: 1px solid rgba(255,255,255,0.10);
    background:
        linear-gradient(135deg, rgba(255,255,255,0.07), rgba(255,255,255,0.03));
    border-radius: 26px;
    padding: 28px 28px 22px 28px;
    box-shadow: var(--shadow);
    margin-bottom: 18px;
}

.hero-title {
    font-size: 2.1rem;
    font-weight: 800;
    line-height: 1.05;
    margin: 0;
    color: white;
    letter-spacing: 0.03em;
}

.hero-subtitle {
    color: var(--muted);
    margin-top: 8px;
    font-size: 0.98rem;
}

.version-chip {
    display: inline-block;
    margin-top: 14px;
    padding: 7px 12px;
    border-radius: 999px;
    background: var(--accent-soft);
    border: 1px solid var(--border-strong);
    color: #FCEEC8 !important;
    font-size: 0.82rem;
    font-weight: 700;
    letter-spacing: 0.03em;
}

.section-card {
    border: 1px solid var(--border);
    background: var(--card);
    border-radius: var(--radius-xl);
    padding: 18px;
    box-shadow: var(--shadow);
    margin-bottom: 14px;
}

.section-title {
    font-size: 0.88rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #F0D99A !important;
    margin-bottom: 10px;
    font-weight: 800;
}

.section-heading {
    font-size: 1.18rem;
    font-weight: 800;
    margin-bottom: 8px;
    color: white;
}

.section-subtext {
    color: var(--muted);
    font-size: 0.92rem;
    margin-bottom: 6px;
}

.guide-box {
    border: 1px solid var(--border);
    border-radius: var(--radius-xl);
    padding: 16px 18px;
    background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.03));
    box-shadow: var(--shadow);
    margin-bottom: 14px;
}
.guide-title {
    font-weight: 800;
    color: var(--accent) !important;
    margin-bottom: 10px;
    letter-spacing: 0.05em;
}
.guide-item {
    color: var(--text);
    padding: 4px 0;
}

.status-good {
    color: #9EF0BD;
    font-weight: 800;
}
.status-bad {
    color: #FFB0B0;
    font-weight: 800;
}

.info-box {
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 12px 14px;
    background: rgba(255,255,255,0.05);
    margin-top: 6px;
    margin-bottom: 12px;
    color: var(--muted);
}

.capture-card {
    border: 1px solid var(--border);
    border-radius: var(--radius-xl);
    padding: 14px;
    background: linear-gradient(180deg, rgba(255,255,255,0.055), rgba(255,255,255,0.03));
    margin-bottom: 12px;
    box-shadow: var(--shadow);
}
.capture-title {
    font-weight: 800;
    color: white !important;
    margin-bottom: 4px;
    font-size: 1rem;
}
.capture-note {
    font-size: 0.82rem;
    color: var(--muted) !important;
    margin-bottom: 8px;
}
.preview-thumb {
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 8px;
    background: rgba(255,255,255,0.035);
}

.range-box {
    border: 1px solid var(--border-strong);
    border-radius: 16px;
    padding: 12px 14px;
    background: rgba(201,164,77,0.09);
    margin-top: 12px;
    margin-bottom: 10px;
    box-shadow: var(--shadow);
}

.preview-card {
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 10px;
    background: rgba(255,255,255,0.04);
    box-shadow: var(--shadow);
}

.result-hero {
    border: 1px solid var(--border-strong);
    border-radius: 22px;
    padding: 18px 20px;
    background:
        linear-gradient(180deg, rgba(201,164,77,0.12), rgba(255,255,255,0.04));
    box-shadow: var(--shadow);
    margin-bottom: 14px;
}
.result-kicker {
    font-size: 0.84rem;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: #F3DE9D !important;
    font-weight: 800;
}
.result-grade {
    font-size: 3.1rem;
    font-weight: 900;
    line-height: 1;
    color: white;
    margin: 6px 0 0 0;
}
.result-copy {
    color: var(--muted);
    margin-top: 8px;
}

.admin-divider {
    margin-top: 26px;
    margin-bottom: 14px;
}

.stAlert {
    border-radius: 16px !important;
}

[data-testid="stDataFrame"] {
    border-radius: 16px;
    overflow: hidden;
    border: 1px solid var(--border);
    box-shadow: var(--shadow);
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero-wrap">
    <div class="hero-title">VOODOO SPORTS GRADING</div>
    <div class="hero-subtitle">Premium card grading workflow with image analysis, confidence scoring, and admin benchmarking.</div>
    <div class="version-chip">LOCKED PRODUCTION VERSION · v10.12-ridge-fit-under08</div>
</div>
""", unsafe_allow_html=True)

# ============================================================
# CONFIG
# ============================================================

MODEL_VERSION = "v10.12-ridge-fit-under08"
PRODUCTION_STATUS = "LOCKED PRODUCTION VERSION"

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
if "analysis_corner_bytes" not in st.session_state:
    st.session_state.analysis_corner_bytes = {}
if "slot_versions" not in st.session_state:
    st.session_state.slot_versions = {}
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


def parse_bool(value) -> bool:
    if value is None:
        return False
    try:
        if pd.isna(value):
            return False
    except Exception:
        pass
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ["true", "1", "yes", "y"]


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
    return 6.0


def corner_subgrade(corner: float) -> float:
    return corner_grade_band(corner)


def edge_subgrade(edge: float) -> float:
    return edge_grade_band(edge)


def surface_subgrade(surface: float) -> float:
    return surface_grade_band(surface)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def csv_download_bytes(df: pd.DataFrame) -> bytes:
    buffer = io.StringIO()
    df.to_csv(buffer, index=False, quoting=csv.QUOTE_MINIMAL)
    return buffer.getvalue().encode("utf-8")


def get_user_submissions(submitted_by_email: str) -> pd.DataFrame:
    try:
        resp = requests.get(
            f"{TABLE_URL}?submitted_by=eq.{submitted_by_email}&order=created_at.desc",
            headers=headers,
            timeout=30,
        )
        if resp.status_code != 200:
            return pd.DataFrame()
        data = resp.json()
        if not isinstance(data, list):
            return pd.DataFrame()
        return pd.DataFrame(data)
    except Exception:
        return pd.DataFrame()


def build_user_export_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    preferred_cols = [
        "created_at",
        "card_id",
        "player_name",
        "manufacturer",
        "stock_type",
        "calibrated_grade",
        "confidence_percent",
        "confidence_label",
        "submit_label",
        "submit_percent",
        "horizontal_ratio",
        "vertical_ratio",
        "corner_score",
        "edge_score",
        "surface_score",
        "front_image_url",
        "back_image_url",
        "corner1_image_url",
        "corner2_image_url",
        "corner3_image_url",
        "corner4_image_url",
    ]
    export_cols = [c for c in preferred_cols if c in df.columns]
    return df[export_cols].copy()


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
        overflow: hidden;
        border: 1px solid #666;
        border-radius: 8px;
    ">
        <img
            src="data:image/png;base64,{img_b64}"
            style="
                position:absolute;
                top:0;
                left:0;
                width:{width}px;
                height:{height}px;
                object-fit:contain;
                z-index:1;
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

    w, h = preview.size

    if horizontal_ratio is None or vertical_ratio is None:
        return preview

    try:
        r_h = max(0.01, min(1.0, float(horizontal_ratio)))
        r_v = max(0.01, min(1.0, float(vertical_ratio)))
    except Exception:
        return preview

    left_prop = r_h / (1 + r_h)
    right_prop = 1 / (1 + r_h)
    top_prop = r_v / (1 + r_v)
    bottom_prop = 1 / (1 + r_v)

    left_x = int(w * left_prop)
    right_x = int(w * right_prop)
    top_y = int(h * top_prop)
    bottom_y = int(h * bottom_prop)

    return preview, left_x, right_x, top_y, bottom_y


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


def validation_status(label: str, passed: bool):
    text = "OK" if passed else "Missing"
    css = "status-good" if passed else "status-bad"
    st.markdown(f"{label}: <span class='{css}'>{text}</span>", unsafe_allow_html=True)


def reset_analysis_state():
    st.session_state.analysis_complete = False
    st.session_state.analysis_payload = None
    st.session_state.analysis_front_bytes = None
    st.session_state.analysis_back_bytes = None
    st.session_state.analysis_corner_bytes = {}
    st.session_state.player_name_edit = ""
    st.session_state.last_save_success = False


def clear_slot(slot_name: str):
    current = st.session_state.slot_versions.get(slot_name, 0)
    st.session_state.slot_versions[slot_name] = current + 1
    reset_analysis_state()
    st.rerun()


def current_slot_version(slot_name: str) -> int:
    return st.session_state.slot_versions.get(slot_name, 0)


def render_image_slot(label: str, slot_name: str, required: bool):
    slot_version = current_slot_version(slot_name)
    options = ["Upload", "Take Photo"]
    if not required:
        options = ["None", "Upload", "Take Photo"]

    mode = st.radio(
        f"{label} Source",
        options,
        horizontal=True,
        key=f"{slot_name}_mode_{st.session_state.upload_key}_{slot_version}",
        label_visibility="collapsed",
    )

    st.markdown('<div class="capture-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="capture-title">{label}</div>', unsafe_allow_html=True)

    obj = None
    if mode == "Upload":
        st.markdown('<div class="capture-note">Choose an existing image from your device.</div>', unsafe_allow_html=True)
        obj = st.file_uploader(
            "",
            ["jpg", "jpeg", "png"],
            key=f"{slot_name}_upload_{st.session_state.upload_key}_{slot_version}",
            label_visibility="collapsed",
        )
    elif mode == "Take Photo":
        st.markdown('<div class="capture-note">Take a new photo directly in the app.</div>', unsafe_allow_html=True)
        obj = st.camera_input(
            "",
            key=f"{slot_name}_camera_{st.session_state.upload_key}_{slot_version}",
            label_visibility="collapsed",
        )
    else:
        st.markdown('<div class="capture-note">No image selected for this slot.</div>', unsafe_allow_html=True)

    if obj is not None:
        preview_col, action_col = st.columns([1, 1])
        with preview_col:
            st.markdown('<div class="preview-thumb">', unsafe_allow_html=True)
            st.image(obj, width=145)
            st.markdown("</div>", unsafe_allow_html=True)
        with action_col:
            st.write("Ready")
            if st.button(f"Clear {label}", key=f"{slot_name}_clear_btn_{st.session_state.upload_key}_{slot_version}"):
                st.markdown("</div>", unsafe_allow_html=True)
                clear_slot(slot_name)

    st.markdown("</div>", unsafe_allow_html=True)
    return obj, mode


def upload_optional_image(image_bytes, filename):
    if image_bytes is None:
        return None

    resp = requests.post(
        f"{SUPABASE_URL}/storage/v1/object/card-images/{filename}",
        headers=upload_headers,
        data=image_bytes,
        timeout=60,
    )
    if resp.status_code not in [200, 201]:
        raise RuntimeError(resp.text)

    return f"{SUPABASE_URL}/storage/v1/object/public/card-images/{filename}"

# ============================================================
# HISTORICAL GRADE RANGE HELPERS
# ============================================================

GRADE_BANDS = [
    ("10 Candidate", 9.7, 10.01),
    ("9.5-9.6", 9.5, 9.7),
    ("9.0-9.4", 9.0, 9.5),
    ("8.5-8.9", 8.5, 9.0),
    ("8.0-8.4", 8.0, 8.5),
    ("Below 8.0", -999.0, 8.0),
]


def predicted_grade_band(value: float) -> str:
    try:
        g = float(value)
    except Exception:
        return "Unknown"
    for label, low, high in GRADE_BANDS:
        if low <= g < high:
            return label
    return "Unknown"


def add_grade_band_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    if "calibrated_grade" in out.columns:
        out["predicted_grade_band"] = out["calibrated_grade"].apply(predicted_grade_band)
    return out


def build_grade_range_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    needed = ["calibrated_grade", "psa_actual_grade"]
    if not all(c in df.columns for c in needed):
        return pd.DataFrame()

    work = df.dropna(subset=needed).copy()
    if work.empty:
        return pd.DataFrame()

    work = add_grade_band_columns(work)
    work["error"] = work["calibrated_grade"] - work["psa_actual_grade"]
    work["abs_error"] = work["error"].abs()

    rows = []
    for band, g in work.groupby("predicted_grade_band", dropna=False):
        rows.append({
            "predicted_grade_band": band,
            "sample_size": len(g),
            "mae": round(float(g["abs_error"].mean()), 3),
            "bias": round(float(g["error"].mean()), 3),
            "range_low": round(float(g["psa_actual_grade"].quantile(0.10)), 2),
            "range_high": round(float(g["psa_actual_grade"].quantile(0.90)), 2),
        })

    out = pd.DataFrame(rows)
    if out.empty:
        return out

    band_order = {label: idx for idx, (label, _, _) in enumerate(GRADE_BANDS)}
    out["sort_order"] = out["predicted_grade_band"].map(lambda x: band_order.get(x, 999))
    out = out.sort_values(["sort_order", "predicted_grade_band"]).drop(columns=["sort_order"])
    return out.reset_index(drop=True)


def lookup_grade_range(predicted_grade: float, range_table: pd.DataFrame) -> dict:
    if range_table is None or range_table.empty:
        return {
            "band": predicted_grade_band(predicted_grade),
            "range_low": round(max(1.0, predicted_grade - 0.5), 2),
            "range_high": round(min(10.0, predicted_grade + 0.5), 2),
            "mae": None,
            "sample_size": 0,
            "source": "fallback",
        }

    band = predicted_grade_band(predicted_grade)
    match = range_table[range_table["predicted_grade_band"] == band]
    if match.empty:
        return {
            "band": band,
            "range_low": round(max(1.0, predicted_grade - 0.5), 2),
            "range_high": round(min(10.0, predicted_grade + 0.5), 2),
            "mae": None,
            "sample_size": 0,
            "source": "fallback",
        }

    row = match.iloc[0]
    return {
        "band": band,
        "range_low": float(row["range_low"]),
        "range_high": float(row["range_high"]),
        "mae": float(row["mae"]),
        "sample_size": int(row["sample_size"]),
        "source": "historical",
    }

# ============================================================
# GRADING MODELS
# ============================================================

def compute_base_raw_grade(
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


def compute_fitted_grade(
    horizontal_ratio: float,
    vertical_ratio: float,
    corner_score: float,
    edge_score: float,
    surface_score: float
) -> float:
    base_raw_grade = (
        8.35
        + 0.25 * (1.0 - float(vertical_ratio))
        - 0.47 * float(corner_score)
        - 0.94 * float(edge_score)
        + 38.67 * float(surface_score)
        - 350.94 * (float(surface_score) ** 2)
    )

    grade = (
        6.352746894335614
        + 0.2125517452912357 * float(base_raw_grade)
        + 1.0969743530394758 * float(vertical_ratio)
        + 0.6867993814790476 * float(corner_score)
        + 0.19836153854880495 * float(edge_score)
        - 0.16523592748691407 * float(surface_score)
    )

    return round(max(1.0, min(10.0, grade)), 2)


def apply_piecewise_grade(surface_score: float, edge_score: float, horizontal_ratio: float) -> float:
    s = float(surface_score)
    e = float(edge_score)
    h = float(horizontal_ratio)

    if s <= 0.1213:
        if e <= 0.01355:
            grade = 9.3947
        else:
            grade = 8.0
    else:
        if h <= 0.7933:
            grade = 6.5
        else:
            grade = 8.75

    return round(max(1.0, min(10.0, grade)), 2)


def apply_calibration(
    raw_grade: float,
    surface: float,
    corner: float,
    edge: float,
    h: float,
    v: float,
    corner_count_used: int,
    used_surface_fallback: bool,
    manual_centering_used: bool,
):
    grade = compute_fitted_grade(
        horizontal_ratio=h,
        vertical_ratio=v,
        corner_score=corner,
        edge_score=edge,
        surface_score=surface,
    )
    return grade, "ridge_fit_from_confirmed_psa_rows"


def compute_psa_caps(h: float, v: float, edge: float, corner: float, surface: float) -> dict:
    centering_cap = centering_psa_grade(h, v)
    corner_cap = corner_grade_band(corner)
    edge_cap = edge_grade_band(edge)
    surface_cap = surface_grade_band(surface)

    fitted_grade = compute_fitted_grade(h, v, corner, edge, surface)
    piecewise_grade = apply_piecewise_grade(surface_score=surface, edge_score=edge, horizontal_ratio=h)

    cap_values = {
        "Centering": centering_cap,
        "Corners": corner_cap,
        "Edges": edge_cap,
        "Surface": surface_cap,
    }
    limiting_feature = min(cap_values, key=cap_values.get)

    return {
        "overall_grade": fitted_grade,
        "candidate_grade": fitted_grade,
        "raw_candidate_grade": compute_base_raw_grade(h, v, corner, edge, surface),
        "piecewise_candidate_grade": piecewise_grade,
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

# ============================================================
# CONFIDENCE
# ============================================================

def boundary_distance_confidence(surface: float, edge: float, h: float) -> float:
    d_surface = abs(float(surface) - 0.1213)
    d_edge = abs(float(edge) - 0.01355)
    d_center = abs(float(h) - 0.7933)

    score = (
        min(d_surface / 0.03, 1.0) +
        min(d_edge / 0.01, 1.0) +
        min(d_center / 0.10, 1.0)
    ) / 3.0

    return max(0.0, min(1.0, score))


def model_agreement_confidence(fitted_grade: float, piecewise_grade: float) -> float:
    diff = abs(float(fitted_grade) - float(piecewise_grade))
    return max(0.0, min(1.0, 1.0 - (diff / 2.5)))


def compute_confidence(
    h: float,
    v: float,
    edge: float,
    corner: float,
    surface: float,
    fitted_grade: float,
    piecewise_grade: float,
    used_surface_fallback: bool = False,
    corner_count: int = 0
) -> dict:
    boundary_score = boundary_distance_confidence(surface=surface, edge=edge, h=h)
    agreement_score = model_agreement_confidence(fitted_grade=fitted_grade, piecewise_grade=piecewise_grade)

    data_score = 1.0
    if used_surface_fallback:
        data_score -= 0.20
    if corner_count < 2:
        data_score -= 0.20
    elif corner_count == 2:
        data_score -= 0.05

    data_score = max(0.0, min(1.0, data_score))

    confidence_raw = (
        0.50 * boundary_score +
        0.30 * agreement_score +
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
        "boundary_score": round(boundary_score, 3),
        "agreement_score": round(agreement_score, 3),
        "data_score": round(data_score, 3),
        "band_spread": None,
        "centering_band": centering_psa_grade(h, v),
        "corner_band": corner_grade_band(corner),
        "edge_band": edge_grade_band(edge),
        "surface_band": surface_grade_band(surface),
    }

# ============================================================
# SUBMIT RULES
# ============================================================

def compute_submit_probability(
    grade: float,
    confidence_score: float,
    surface: float,
    band_spread
) -> dict:
    confidence_percent = confidence_score * 100.0

    if grade >= 9.3 and confidence_percent >= 85.0:
        label = "Strong Submit"
        probability = 0.95
    elif grade >= 9.3 and confidence_percent < 85.0:
        label = "Submit"
        probability = 0.80
    elif 8.4 < grade < 9.3 and confidence_percent > 80.0:
        label = "Risky"
        probability = 0.55
    else:
        label = "Do Not Submit"
        probability = 0.15

    return {
        "submit_probability": round(probability, 3),
        "submit_percent": round(probability * 100, 1),
        "submit_label": label,
    }

# ============================================================
# RESULT PANELS
# ============================================================

def decision_panel_admin(
    grade: float,
    h: float,
    v: float,
    edge: float,
    corner: float,
    surface: float,
    confidence: dict,
    submit: dict,
    grade_range: dict,
    raw_grade: float,
    piecewise_grade: float,
    grading_path: str
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

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Submission Decision</div>', unsafe_allow_html=True)
    st.write("Submit Probability:", f"{submit['submit_percent']:.1f}%")
    st.write("Recommendation:", submit["submit_label"])
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Confidence</div>', unsafe_allow_html=True)
    st.write("Confidence Score:", f"{confidence['confidence_percent']:.1f}%")
    st.write("Confidence Level:", confidence["confidence_label"])
    st.write(
        "Risk Level:",
        "Low" if confidence["confidence_score"] >= 0.75 else
        "Moderate" if confidence["confidence_score"] >= 0.55 else
        "High"
    )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Expected PSA Range</div>', unsafe_allow_html=True)
    st.write("Predicted Band:", grade_range["band"])
    st.write("Expected PSA Range:", f"{grade_range['range_low']:.2f} to {grade_range['range_high']:.2f}")
    if grade_range["mae"] is not None:
        st.write("Current Margin of Error (MAE):", round(float(grade_range["mae"]), 3))
        st.write("Historical Sample Size:", grade_range["sample_size"])
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Centering</div>', unsafe_allow_html=True)
    st.write("Horizontal Centering:", ratio_to_psa_centering(h))
    st.write("Vertical Centering:", ratio_to_psa_centering(v))
    st.write("Centering Grade:", centering_psa_grade(h, v))
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Subgrades</div>', unsafe_allow_html=True)
    st.write("Corners:", corner_subgrade(corner))
    st.write("Edges:", edge_subgrade(edge))
    st.write("Surface:", surface_subgrade(surface))
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Confidence Breakdown</div>', unsafe_allow_html=True)
    st.write("Boundary Score:", confidence["boundary_score"])
    st.write("Model Agreement Score:", confidence["agreement_score"])
    st.write("Data Quality Score:", confidence["data_score"])
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Formula Output</div>', unsafe_allow_html=True)
    st.write("Base Raw Formula Grade:", raw_grade)
    st.write("Piecewise Comparison Grade:", piecewise_grade)
    st.write("Final Grade:", grade)
    st.write("Grading Path:", grading_path)
    st.write("Centering Band:", caps["centering_cap"])
    st.write("Corner Band:", caps["corner_cap"])
    st.write("Edge Band:", caps["edge_cap"])
    st.write("Surface Band:", caps["surface_cap"])
    st.markdown("</div>", unsafe_allow_html=True)


def decision_panel_user(
    grade: float,
    h: float,
    v: float,
    corner: float,
    edge: float,
    surface: float,
    confidence: dict,
    submit: dict,
    grade_range: dict
) -> None:
    if submit["submit_label"] == "Strong Submit":
        st.success("STRONG SUBMIT")
    elif submit["submit_label"] == "Submit":
        st.success("SUBMIT")
    elif submit["submit_label"] == "Risky":
        st.warning("RISKY")
    else:
        st.error("DO NOT SUBMIT")

    st.markdown(f"""
    <div class="result-hero">
        <div class="result-kicker">Grading Result</div>
        <div class="result-grade">{grade}</div>
        <div class="result-copy">Confidence and submission recommendation shown below.</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Grade", grade)
    with col2:
        st.metric("Confidence", f"{confidence['confidence_percent']:.1f}%")
    with col3:
        st.metric("Submit", submit["submit_label"])

    st.markdown(f"""
    <div class="range-box">
        <div><strong>Expected PSA Range:</strong> {grade_range['range_low']:.2f} to {grade_range['range_high']:.2f}</div>
        <div><strong>Current Margin of Error:</strong> {"N/A" if grade_range['mae'] is None else round(float(grade_range['mae']), 3)}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Centering</div>', unsafe_allow_html=True)
    st.write("Horizontal:", ratio_to_psa_centering(h))
    st.write("Vertical:", ratio_to_psa_centering(v))
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Subgrades</div>', unsafe_allow_html=True)
    st.write("Corners:", corner_subgrade(corner))
    st.write("Edges:", edge_subgrade(edge))
    st.write("Surface:", surface_subgrade(surface))
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# ACCESS + GUIDE
# ============================================================

st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">Access</div>', unsafe_allow_html=True)
st.markdown('<div class="section-heading">Sign in to continue</div>', unsafe_allow_html=True)
st.markdown('<div class="section-subtext">Use your authorized access email to open grading and admin tools.</div>', unsafe_allow_html=True)
user_email = st.text_input("Enter Access Email")
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("""
<div class="guide-box">
    <div class="guide-title">USER GUIDE BEST PRACTICES</div>
    <div class="guide-item">• All pictures taken from same height/zoom with similar lighting</div>
    <div class="guide-item">• Take pictures of all 4 front corners</div>
    <div class="guide-item">• Use manual centering</div>
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
# LOAD DATA FOR RANGE + ADMIN
# ============================================================

all_submissions_df = pd.DataFrame()
range_table = pd.DataFrame()

try:
    range_resp = requests.get(TABLE_URL, headers=headers, timeout=30)
    if range_resp.status_code == 200:
        all_submissions_df = pd.DataFrame(range_resp.json())
        range_table = build_grade_range_table(all_submissions_df)
except Exception:
    all_submissions_df = pd.DataFrame()
    range_table = pd.DataFrame()

# ============================================================
# USER DATA DOWNLOAD
# ============================================================

st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">My Submission Data</div>', unsafe_allow_html=True)
st.markdown('<div class="section-subtext">Load and export your saved submissions.</div>', unsafe_allow_html=True)

if st.button("Load My Submission Data"):
    user_df = get_user_submissions(user_email)

    if user_df.empty:
        st.warning("No submissions found for this email.")
    else:
        export_df = build_user_export_df(user_df)
        st.success(f"Found {len(export_df)} submission(s).")
        st.dataframe(export_df, use_container_width=True, hide_index=True)

        safe_email = user_email.replace("@", "_at_").replace(".", "_")
        st.download_button(
            "Download My CSV",
            data=csv_download_bytes(export_df),
            file_name=f"voodoo_submissions_{safe_email}.csv",
            mime="text/csv",
        )
st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# CARD INFO
# ============================================================

st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">Card Information</div>', unsafe_allow_html=True)
user_entered_player_name = st.text_input("Player Name")
manufacturer = st.text_input("Manufacturer")
stock_type = st.selectbox("Stock Type", ["paper", "chrome", "refractor", "foil", "other"])

psa_is_graded = st.checkbox("PSA graded?")
psa_actual_grade = None
if psa_is_graded:
    psa_actual_grade = st.number_input("PSA Grade", 1.0, 10.0, step=0.5)
st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# IMAGE INPUTS
# ============================================================

st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">Card Images</div>', unsafe_allow_html=True)
st.markdown('<div class="section-subtext">Capture a clean full front, full back, and at least two corners.</div>', unsafe_allow_html=True)

clear_col, _ = st.columns([1, 3])
with clear_col:
    if st.button("Clear All Images"):
        st.session_state.upload_key = str(uuid.uuid4())
        st.session_state.slot_versions = {}
        reset_analysis_state()
        st.rerun()

st.markdown("""
<div class="info-box">
Each image slot shows only one action at a time. Choose Upload or Take Photo, then review the preview. Use the slot clear button to replace only that image.
</div>
""", unsafe_allow_html=True)

front_image_obj, front_mode = render_image_slot("Front Image", "front", required=True)
back_image_obj, back_mode = render_image_slot("Back Image", "back", required=True)

st.markdown('<div class="section-title" style="margin-top:6px;">Corner Images</div>', unsafe_allow_html=True)
st.markdown('<div class="section-subtext">Two required. All four recommended.</div>', unsafe_allow_html=True)
corner1_obj, corner1_mode = render_image_slot("Corner 1", "corner1", required=True)
corner2_obj, corner2_mode = render_image_slot("Corner 2", "corner2", required=True)
corner3_obj, corner3_mode = render_image_slot("Corner 3", "corner3", required=False)
corner4_obj, corner4_mode = render_image_slot("Corner 4", "corner4", required=False)
st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# VALIDATION PANEL
# ============================================================

st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">Ready Check</div>', unsafe_allow_html=True)
front_ok = front_image_obj is not None
back_ok = back_image_obj is not None
corner_count_current = sum(1 for c in [corner1_obj, corner2_obj, corner3_obj, corner4_obj] if c is not None)
corners_ok = corner_count_current >= 2

v1, v2, v3 = st.columns(3)
with v1:
    validation_status("Front Image", front_ok)
with v2:
    validation_status("Back Image", back_ok)
with v3:
    validation_status("Corner Images (2+)", corners_ok)
st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# MANUAL CENTERING ASSIST
# ============================================================

st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">Manual Centering Assist</div>', unsafe_allow_html=True)
use_manual_centering = st.checkbox("Use front centering assist")

manual_left = manual_right = manual_top = manual_bottom = None
manual_h_ratio = manual_v_ratio = None
manual_centering_valid = True

if use_manual_centering:
    if front_image_obj is None:
        st.info("Provide a front image to use centering assist.")
        manual_centering_valid = False
    else:
        try:
            front_image = Image.open(front_image_obj).convert("RGB")
            front_image = front_image.transpose(Image.Transpose.ROTATE_90)
        except Exception as e:
            st.error(f"Could not open front image: {e}")
            st.stop()

        max_display_width = 320
        scale = min(1.0, max_display_width / front_image.width)
        display_width = int(front_image.width * scale)
        display_height = int(front_image.height * scale)
        display_image = front_image.resize((display_width, display_height))

        st.markdown(
            '<div class="small-note">Image rotated 180 degrees counterclockwise for manual centering. Use fine sliders for precise mobile adjustment.</div>',
            unsafe_allow_html=True
        )

        left_percent = st.slider("Left", 0.0, 100.0, 1.0, step=0.1)
        right_percent = st.slider("Right", 0.0, 100.0, 99.0, step=0.1)
        top_percent = st.slider("Top", 0.0, 100.0, 1.0, step=0.1)
        bottom_percent = st.slider("Bottom", 0.0, 100.0, 99.0, step=0.1)

        left_x = (left_percent / 100.0) * display_width
        right_x = (right_percent / 100.0) * display_width
        top_y = (top_percent / 100.0) * display_height
        bottom_y = (bottom_percent / 100.0) * display_height

        render_overlay_image(display_image, left_x, right_x, top_y, bottom_y)

        if right_x <= left_x or bottom_y <= top_y:
            st.error("Right must be right of left, and bottom must be below top.")
            manual_centering_valid = False
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
st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# RUN ANALYSIS
# ============================================================

if st.button("Run Analysis"):
    st.session_state.last_save_success = False
    reset_analysis_state()

    if not front_ok:
        st.error("Front image required")
        st.stop()
    if not back_ok:
        st.error("Back image required")
        st.stop()
    if not corners_ok:
        st.error("At least 2 corner images are required")
        st.stop()
    if use_manual_centering and not manual_centering_valid:
        st.error("Manual centering values are not valid")
        st.stop()

    front_bytes = front_image_obj.getvalue()
    back_bytes = back_image_obj.getvalue()
    front_image_hash = sha256_bytes(front_bytes)

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

    h = float(data["horizontal_ratio"])
    v = float(data["vertical_ratio"])
    edge = float(data["edge_score"])

    if use_manual_centering and manual_h_ratio is not None and manual_v_ratio is not None:
        h = float(manual_h_ratio)
        v = float(manual_v_ratio)
        st.info("Manual front centering applied")

    corner_inputs = {
        "corner1": corner1_obj,
        "corner2": corner2_obj,
        "corner3": corner3_obj,
        "corner4": corner4_obj,
    }

    corner_scores = []
    corner_bytes_map = {}

    for slot_name, c in corner_inputs.items():
        if c is None:
            continue
        c_bytes = c.getvalue()
        corner_bytes_map[slot_name] = c_bytes
        try:
            cr = requests.post(
                f"{API_BASE}/analyze_corner",
                files={"file": ("corner.jpg", c_bytes, "image/jpeg")},
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

        corner_scores.append(float(corner_data["corner_score"]))

    if len(corner_scores) == 0:
        corner = 0.5
        corner_count_used = 0
        st.warning("All corner analyses failed. Using neutral corner score.")
    else:
        corner = min(corner_scores)
        corner_count_used = len(corner_scores)

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

    if user_entered_player_name and str(user_entered_player_name).strip():
        st.session_state.player_name_edit = str(user_entered_player_name).strip()
    else:
        st.session_state.player_name_edit = detected_player_name if detected_player_name else ""

    raw_grade = compute_base_raw_grade(h, v, corner, edge, float(surface))
    piecewise_grade = apply_piecewise_grade(surface_score=float(surface), edge_score=edge, horizontal_ratio=h)
    grade, grading_path = apply_calibration(
        raw_grade=raw_grade,
        surface=surface,
        corner=corner,
        edge=edge,
        h=h,
        v=v,
        corner_count_used=corner_count_used,
        used_surface_fallback=used_surface_fallback,
        manual_centering_used=use_manual_centering,
    )

    confidence = compute_confidence(
        h=h,
        v=v,
        edge=edge,
        corner=corner,
        surface=float(surface),
        fitted_grade=grade,
        piecewise_grade=piecewise_grade,
        used_surface_fallback=used_surface_fallback,
        corner_count=corner_count_used,
    )

    submit = compute_submit_probability(
        grade=grade,
        confidence_score=confidence["confidence_score"],
        surface=float(surface),
        band_spread=confidence["band_spread"],
    )

    grade_range = lookup_grade_range(grade, range_table)

    preview_pack = build_card_preview_with_overlay(
        image_bytes=front_bytes,
        horizontal_ratio=h,
        vertical_ratio=v,
        max_width=405
    )

    st.session_state.analysis_payload = {
        "user_entered_player_name": user_entered_player_name,
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
        "grade": grade,
        "raw_grade": raw_grade,
        "piecewise_grade": piecewise_grade,
        "grading_path": grading_path,
        "grade_range": grade_range,
        "confidence": confidence,
        "submit": submit,
        "preview_pack": preview_pack,
        "detected_player_name": detected_player_name,
        "detected_player_confidence": detected_player_confidence,
        "detected_player_source": detected_player_source,
        "corner_count": corner_count_used,
        "front_image_hash": front_image_hash,
        "front_source_mode": front_mode,
        "back_source_mode": back_mode,
        "corner1_source_mode": corner1_mode,
        "corner2_source_mode": corner2_mode,
        "corner3_source_mode": corner3_mode if corner3_obj is not None else None,
        "corner4_source_mode": corner4_mode if corner4_obj is not None else None,
    }
    st.session_state.analysis_front_bytes = front_bytes
    st.session_state.analysis_back_bytes = back_bytes
    st.session_state.analysis_corner_bytes = corner_bytes_map
    st.session_state.analysis_complete = True

# ============================================================
# RESULTS / SAVE
# ============================================================

if st.session_state.analysis_complete and st.session_state.analysis_payload is not None:
    result = st.session_state.analysis_payload

    detected_player_name = result["detected_player_name"]
    detected_player_confidence = result["detected_player_confidence"]
    detected_player_source = result["detected_player_source"]
    typed_player_name = result.get("user_entered_player_name")

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Player Name</div>', unsafe_allow_html=True)
    if detected_player_name:
        msg = f"Detected player: {detected_player_name}"
        if detected_player_confidence is not None:
            try:
                msg += f" ({round(float(detected_player_confidence) * 100, 1)}%)"
            except Exception:
                pass
        st.write(msg)
    else:
        st.write("Detected player: Not found")

    st.text_input("Player Name (edit or confirm before save)", key="player_name_edit")
    st.markdown("</div>", unsafe_allow_html=True)

    final_player_name = st.session_state.player_name_edit.strip() if st.session_state.player_name_edit else None

    if final_player_name:
        if detected_player_name and final_player_name == detected_player_name:
            final_player_name_confidence = detected_player_confidence
            final_player_name_source = detected_player_source
        elif typed_player_name and final_player_name == str(typed_player_name).strip():
            final_player_name_confidence = None
            final_player_name_source = "user_entered"
        else:
            final_player_name_confidence = None
            final_player_name_source = "manual_override"
    else:
        final_player_name_confidence = detected_player_confidence if detected_player_name else None
        final_player_name_source = detected_player_source

    if result["preview_pack"] is not None:
        preview_img, left_x, right_x, top_y, bottom_y = result["preview_pack"]
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Card Preview</div>', unsafe_allow_html=True)
        st.markdown('<div class="preview-card">', unsafe_allow_html=True)
        render_overlay_image(preview_img, left_x, right_x, top_y, bottom_y)
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

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
            result["grade_range"],
            result["raw_grade"],
            result["piecewise_grade"],
            result["grading_path"],
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
            result["grade_range"],
        )

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">About to Save</div>', unsafe_allow_html=True)
    s1, s2, s3 = st.columns(3)
    with s1:
        st.write("Player Name:", final_player_name or "—")
        st.write("Manufacturer:", result["manufacturer"] or "—")
    with s2:
        st.write("Stock Type:", result["stock_type"] or "—")
        st.write("Grade:", result["grade"])
    with s3:
        st.write("Confidence:", f"{result['confidence']['confidence_percent']:.1f}%")
        st.write("Submit:", result["submit"]["submit_label"])
    st.markdown("</div>", unsafe_allow_html=True)

    if user_role == "admin":
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Raw Feature Values</div>', unsafe_allow_html=True)
        st.write("Horizontal Ratio:", round(result["horizontal_ratio"], 4))
        st.write("Vertical Ratio:", round(result["vertical_ratio"], 4))
        st.write("Horizontal Centering:", ratio_to_psa_centering(result["horizontal_ratio"]))
        st.write("Vertical Centering:", ratio_to_psa_centering(result["vertical_ratio"]))
        st.write("Corner Score:", round(result["corner_score"], 4))
        st.write("Adjusted Corner Score:", round(remap_corner_for_model(result["corner_score"]), 4))
        st.write("Edge Score:", round(result["edge_score"], 4))
        st.write("Surface Score:", round(float(result["surface_score"]), 4))
        st.write("Base Raw Formula Grade:", round(float(result["raw_grade"]), 2))
        st.write("Piecewise Comparison Grade:", round(float(result["piecewise_grade"]), 2))
        st.write("Final Grade:", round(float(result["grade"]), 2))
        st.write("Corner Count Used:", result["corner_count"])
        st.write("Used Surface Fallback:", result["used_surface_fallback"])
        st.write("Grading Path:", result["grading_path"])
        st.write("Boundary Score:", result["confidence"]["boundary_score"])
        st.write("Model Agreement Score:", result["confidence"]["agreement_score"])
        st.write("Data Quality Score:", result["confidence"]["data_score"])
        st.write("Front Source:", result["front_source_mode"])
        st.write("Back Source:", result["back_source_mode"])
        if result["scratch_score"] is not None:
            st.write("Scratch Score:", round(float(result["scratch_score"]), 4))
        if result["speckle_score"] is not None:
            st.write("Speckle Score:", round(float(result["speckle_score"]), 4))
        if result["gloss_score"] is not None:
            st.write("Gloss Score:", round(float(result["gloss_score"]), 4))
        st.markdown("</div>", unsafe_allow_html=True)

    if st.button("Save Submission"):
        front_bytes = st.session_state.analysis_front_bytes
        back_bytes = st.session_state.analysis_back_bytes
        corner_bytes_map = st.session_state.analysis_corner_bytes

        if front_bytes is None:
            st.error("Missing analyzed front image bytes.")
            st.stop()

        card_id = str(uuid.uuid4())
        front_name = f"{card_id}_front.jpg"
        back_name = f"{card_id}_back.jpg"

        try:
            front_url = upload_optional_image(front_bytes, front_name)
        except Exception as e:
            st.error(f"Front upload failed: {e}")
            st.stop()

        back_url = None
        if back_bytes is not None:
            try:
                back_url = upload_optional_image(back_bytes, back_name)
            except Exception as e:
                st.error(f"Back upload failed: {e}")
                st.stop()

        try:
            corner1_url = upload_optional_image(corner_bytes_map.get("corner1"), f"{card_id}_corner1.jpg")
            corner2_url = upload_optional_image(corner_bytes_map.get("corner2"), f"{card_id}_corner2.jpg")
            corner3_url = upload_optional_image(corner_bytes_map.get("corner3"), f"{card_id}_corner3.jpg")
            corner4_url = upload_optional_image(corner_bytes_map.get("corner4"), f"{card_id}_corner4.jpg")
        except Exception as e:
            st.error(f"Corner upload failed: {e}")
            st.stop()

        payload = {
            "card_id": card_id,
            "model_version": MODEL_VERSION,
            "manufacturer": json_safe(result["manufacturer"]),
            "stock_type": json_safe(result["stock_type"]),
            "psa_is_graded": json_safe(result["psa_is_graded"]),
            "psa_actual_grade": json_safe(result["psa_actual_grade"]),
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
            "raw_formula_grade": json_safe(result["raw_grade"]),
            "calibrated_grade": json_safe(result["grade"]),
            "confidence_score": json_safe(result["confidence"]["confidence_score"]),
            "confidence_percent": json_safe(result["confidence"]["confidence_percent"]),
            "confidence_label": json_safe(result["confidence"]["confidence_label"]),
            "agreement_score": json_safe(result["confidence"]["agreement_score"]),
            "threshold_score": json_safe(result["confidence"]["boundary_score"]),
            "data_score": json_safe(result["confidence"]["data_score"]),
            "band_spread": json_safe(None),
            "submit_probability": json_safe(result["submit"]["submit_probability"]),
            "submit_percent": json_safe(result["submit"]["submit_percent"]),
            "submit_label": json_safe(result["submit"]["submit_label"]),
            "front_image_url": json_safe(front_url),
            "back_image_url": json_safe(back_url),
            "corner1_image_url": json_safe(corner1_url),
            "corner2_image_url": json_safe(corner2_url),
            "corner3_image_url": json_safe(corner3_url),
            "corner4_image_url": json_safe(corner4_url),
            "submitted_by": user_email,
            "created_at": str(datetime.now()),
            "manual_centering_used": json_safe(result["use_manual_centering"]),
            "front_left_measurement": json_safe(result["manual_left"] if result["use_manual_centering"] else None),
            "front_right_measurement": json_safe(result["manual_right"] if result["use_manual_centering"] else None),
            "front_top_measurement": json_safe(result["manual_top"] if result["use_manual_centering"] else None),
            "front_bottom_measurement": json_safe(result["manual_bottom"] if result["use_manual_centering"] else None),
            "front_horizontal_ratio_manual": json_safe(result["manual_h_ratio"] if result["use_manual_centering"] else None),
            "front_vertical_ratio_manual": json_safe(result["manual_v_ratio"] if result["use_manual_centering"] else None),
            "grade_range_low": json_safe(result["grade_range"]["range_low"]),
            "grade_range_high": json_safe(result["grade_range"]["range_high"]),
            "grade_band_sample_size": json_safe(result["grade_range"]["sample_size"]),
            "grade_band_mae": json_safe(result["grade_range"]["mae"]),
            "front_image_hash": json_safe(result["front_image_hash"]),
            "corner_count_used": json_safe(result["corner_count"]),
            "used_surface_fallback": json_safe(result["used_surface_fallback"]),
        }

        save_response = requests.post(TABLE_URL, json=payload, headers=headers, timeout=30)

        if save_response.status_code in [200, 201]:
            st.session_state.last_save_success = True
            st.success("Saved successfully")
            st.info("Images remain loaded. Use the clear buttons above whenever you want to replace them.")
        else:
            st.session_state.last_save_success = False
            st.error(f"Database save failed: {save_response.text}")

# ============================================================
# ADMIN
# ============================================================

if user_role == "admin":
    st.markdown('<div class="premium-shell admin-divider">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Admin Dashboard</div>', unsafe_allow_html=True)

    df = all_submissions_df.copy()
    if df.empty:
        st.warning("No admin data available.")
        st.stop()

    st.write("Total:", len(df))
    df = add_grade_band_columns(df)

    if "psa_actual_grade" in df.columns and "calibrated_grade" in df.columns:
        dfv = df.dropna(subset=["psa_actual_grade", "calibrated_grade"]).copy()
        if len(dfv):
            dfv["error"] = dfv["calibrated_grade"] - dfv["psa_actual_grade"]
            dfv["abs_error"] = dfv["error"].abs()
            m1, m2 = st.columns(2)
            with m1:
                st.metric("MAE", round(abs(dfv["error"]).mean(), 3))
            with m2:
                st.metric("Bias", round(dfv["error"].mean(), 3))
            st.bar_chart(dfv["error"])

    st.markdown('<div class="section-title">Grade Range / Margin of Error Table</div>', unsafe_allow_html=True)
    if not range_table.empty:
        st.dataframe(range_table, use_container_width=True, hide_index=True)
    else:
        st.info("Not enough PSA-linked data yet to build historical grade ranges.")

    st.markdown('<div class="section-title">Diagnostics by Grade Band</div>', unsafe_allow_html=True)
    if "psa_actual_grade" in df.columns and "calibrated_grade" in df.columns:
        band_diag = df.dropna(subset=["psa_actual_grade", "calibrated_grade"]).copy()
        if not band_diag.empty:
            band_diag["error"] = band_diag["calibrated_grade"] - band_diag["psa_actual_grade"]
            band_diag["abs_error"] = band_diag["error"].abs()
            band_summary = band_diag.groupby("predicted_grade_band").agg(
                sample_size=("error", "size"),
                mae=("abs_error", lambda s: round(float(s.mean()), 3)),
                bias=("error", lambda s: round(float(s.mean()), 3)),
                avg_pred=("calibrated_grade", lambda s: round(float(s.mean()), 2)),
                avg_psa=("psa_actual_grade", lambda s: round(float(s.mean()), 2)),
            ).reset_index()
            st.dataframe(band_summary, use_container_width=True, hide_index=True)

    st.markdown('<div class="section-title">Diagnostics by Stock Type</div>', unsafe_allow_html=True)
    if {"stock_type", "psa_actual_grade", "calibrated_grade"}.issubset(df.columns):
        stock_diag = df.dropna(subset=["stock_type", "psa_actual_grade", "calibrated_grade"]).copy()
        if not stock_diag.empty:
            stock_diag["error"] = stock_diag["calibrated_grade"] - stock_diag["psa_actual_grade"]
            stock_diag["abs_error"] = stock_diag["error"].abs()
            stock_summary = stock_diag.groupby("stock_type").agg(
                sample_size=("error", "size"),
                mae=("abs_error", lambda s: round(float(s.mean()), 3)),
                bias=("error", lambda s: round(float(s.mean()), 3)),
            ).reset_index()
            st.dataframe(stock_summary, use_container_width=True, hide_index=True)

    st.markdown('<div class="section-title">Diagnostics by Confidence Label</div>', unsafe_allow_html=True)
    if {"confidence_label", "psa_actual_grade", "calibrated_grade"}.issubset(df.columns):
        conf_diag = df.dropna(subset=["confidence_label", "psa_actual_grade", "calibrated_grade"]).copy()
        if not conf_diag.empty:
            conf_diag["error"] = conf_diag["calibrated_grade"] - conf_diag["psa_actual_grade"]
            conf_diag["abs_error"] = conf_diag["error"].abs()
            conf_summary = conf_diag.groupby("confidence_label").agg(
                sample_size=("error", "size"),
                mae=("abs_error", lambda s: round(float(s.mean()), 3)),
                bias=("error", lambda s: round(float(s.mean()), 3)),
            ).reset_index()
            st.dataframe(conf_summary, use_container_width=True, hide_index=True)

    st.markdown('<div class="section-title">Version Analytics</div>', unsafe_allow_html=True)
    a1, a2 = st.columns(2)
    with a1:
        if "model_version" in df.columns:
            st.write("Rows by Version")
            st.dataframe(
                df["model_version"].value_counts(dropna=False).rename_axis("model_version").reset_index(name="count"),
                use_container_width=True,
                hide_index=True,
            )

        if "submit_label" in df.columns and "model_version" in df.columns:
            submit_breakdown = df.pivot_table(index="model_version", columns="submit_label", aggfunc="size", fill_value=0)
            st.write("Submit Labels by Version")
            st.dataframe(submit_breakdown.reset_index(), use_container_width=True, hide_index=True)

    with a2:
        if "confidence_label" in df.columns and "model_version" in df.columns:
            conf_breakdown = df.pivot_table(index="model_version", columns="confidence_label", aggfunc="size", fill_value=0)
            st.write("Confidence Labels by Version")
            st.dataframe(conf_breakdown.reset_index(), use_container_width=True, hide_index=True)

        if "calibrated_grade" in df.columns and "model_version" in df.columns:
            avg_grade = df.groupby("model_version", dropna=False)["calibrated_grade"].mean().reset_index()
            avg_grade.columns = ["model_version", "avg_calibrated_grade"]
            st.write("Average Grade by Version")
            st.dataframe(avg_grade, use_container_width=True, hide_index=True)

    st.markdown('<div class="section-title">Filters</div>', unsafe_allow_html=True)
    filtered_df = df.copy()

    f1, f2, f3, f4, f5, f6 = st.columns(6)
    with f1:
        version_options = ["All"] + sorted([str(v) for v in filtered_df["model_version"].dropna().unique()]) if "model_version" in filtered_df.columns else ["All"]
        version_filter = st.selectbox("Model Version", version_options)
    with f2:
        submit_options = ["All"] + sorted([str(v) for v in filtered_df["submit_label"].dropna().unique()]) if "submit_label" in filtered_df.columns else ["All"]
        submit_filter = st.selectbox("Submit Label", submit_options)
    with f3:
        submitter_options = ["All"] + sorted([str(v) for v in filtered_df["submitted_by"].dropna().unique()]) if "submitted_by" in filtered_df.columns else ["All"]
        submitter_filter = st.selectbox("Submitted By", submitter_options)
    with f4:
        stock_options = ["All"] + sorted([str(v) for v in filtered_df["stock_type"].dropna().unique()]) if "stock_type" in filtered_df.columns else ["All"]
        stock_filter = st.selectbox("Stock Type", stock_options)
    with f5:
        band_options = ["All"] + sorted([str(v) for v in filtered_df["predicted_grade_band"].dropna().unique()]) if "predicted_grade_band" in filtered_df.columns else ["All"]
        band_filter = st.selectbox("Predicted Grade Band", band_options)
    with f6:
        sort_option = st.selectbox("Sort By", ["Newest", "Biggest PSA Miss", "Highest Grade", "Lowest Grade"])

    c1, c2, c3 = st.columns(3)
    with c1:
        only_psa = st.checkbox("Only PSA rows")
    with c2:
        only_manual = st.checkbox("Only Manual Centering")
    with c3:
        only_high_conf = st.checkbox("Only High Confidence")

    if version_filter != "All" and "model_version" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["model_version"] == version_filter]
    if submit_filter != "All" and "submit_label" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["submit_label"] == submit_filter]
    if submitter_filter != "All" and "submitted_by" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["submitted_by"] == submitter_filter]
    if stock_filter != "All" and "stock_type" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["stock_type"] == stock_filter]
    if band_filter != "All" and "predicted_grade_band" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["predicted_grade_band"] == band_filter]
    if only_psa and "psa_actual_grade" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["psa_actual_grade"].notna()]
    if only_manual and "manual_centering_used" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["manual_centering_used"] == True]
    if only_high_conf and "confidence_label" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["confidence_label"] == "High"]

    if {"psa_actual_grade", "calibrated_grade"}.issubset(filtered_df.columns):
        filtered_df = filtered_df.copy()
        filtered_df["error"] = filtered_df["calibrated_grade"] - filtered_df["psa_actual_grade"]
        filtered_df["abs_error"] = filtered_df["error"].abs()

    if sort_option == "Biggest PSA Miss" and "abs_error" in filtered_df.columns:
        filtered_df = filtered_df.sort_values("abs_error", ascending=False)
    elif sort_option == "Highest Grade" and "calibrated_grade" in filtered_df.columns:
        filtered_df = filtered_df.sort_values("calibrated_grade", ascending=False)
    elif sort_option == "Lowest Grade" and "calibrated_grade" in filtered_df.columns:
        filtered_df = filtered_df.sort_values("calibrated_grade", ascending=True)
    elif "created_at" in filtered_df.columns:
        filtered_df = filtered_df.sort_values("created_at", ascending=False)

    st.write("Filtered Total:", len(filtered_df))

    show_cols = [
        "created_at",
        "submitted_by",
        "model_version",
        "player_name",
        "manufacturer",
        "stock_type",
        "predicted_grade_band",
        "calibrated_grade",
        "psa_actual_grade",
        "error",
        "abs_error",
        "confidence_percent",
        "submit_label",
        "manual_centering_used",
        "corner_count_used",
        "used_surface_fallback",
        "front_image_url",
        "card_id",
    ]
    show_cols = [c for c in show_cols if c in filtered_df.columns]
    if len(show_cols):
        st.dataframe(filtered_df[show_cols], use_container_width=True, hide_index=True)

    st.markdown('<div class="section-title">Biggest PSA Misses</div>', unsafe_allow_html=True)
    if "abs_error" in filtered_df.columns:
        worst = filtered_df.sort_values("abs_error", ascending=False).head(15)
        worst_cols = [c for c in [
            "created_at", "player_name", "manufacturer", "stock_type", "calibrated_grade",
            "psa_actual_grade", "error", "abs_error", "confidence_percent", "submit_label",
            "manual_centering_used", "corner_count_used", "used_surface_fallback", "card_id"
        ] if c in worst.columns]
        st.dataframe(worst[worst_cols], use_container_width=True, hide_index=True)

    st.markdown('<div class="section-title">Manual Centering Comparison</div>', unsafe_allow_html=True)
    if {"manual_centering_used", "psa_actual_grade", "calibrated_grade"}.issubset(df.columns):
        mc = df.dropna(subset=["manual_centering_used", "psa_actual_grade", "calibrated_grade"]).copy()
        if not mc.empty:
            mc["error"] = mc["calibrated_grade"] - mc["psa_actual_grade"]
            mc["abs_error"] = mc["error"].abs()
            mc_summary = mc.groupby("manual_centering_used").agg(
                sample_size=("error", "size"),
                mae=("abs_error", lambda s: round(float(s.mean()), 3)),
                bias=("error", lambda s: round(float(s.mean()), 3)),
                avg_grade=("calibrated_grade", lambda s: round(float(s.mean()), 2)),
            ).reset_index()
            st.dataframe(mc_summary, use_container_width=True, hide_index=True)

    if not filtered_df.empty:
        st.download_button(
            "Download Filtered CSV",
            data=csv_download_bytes(filtered_df),
            file_name=f"voodoo_submissions_{MODEL_VERSION}.csv",
            mime="text/csv",
        )

    st.markdown('<div class="section-title">Model Maintenance</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="info-box">
    This reanalysis reruns current front-image analysis and surface analysis using the saved front image URL,
    reruns current corner analysis if corner image URLs are available,
    reapplies saved manual centering ratios when the original submission used manual centering,
    then applies the ridge-fitted grading rule and the current confidence model.
    </div>
    """, unsafe_allow_html=True)

    if st.button("True Reanalyze Saved Cards"):
        progress = st.progress(0)
        status_box = st.empty()
        total_rows = len(df)

        success_count = 0
        fail_count = 0

        for idx, (_, row) in enumerate(df.iterrows(), start=1):
            new_grade = None
            confidence = {}
            submit = {}
            grading_path = None

            try:
                front_url = row.get("front_image_url")
                if pd.isna(front_url) or not front_url:
                    fail_count += 1
                    progress.progress(idx / max(total_rows, 1))
                    continue

                img_resp = requests.get(front_url, timeout=60)
                if img_resp.status_code != 200:
                    status_box.warning(f"Image fetch failed for card_id {row.get('card_id')}")
                    fail_count += 1
                    progress.progress(idx / max(total_rows, 1))
                    continue

                front_bytes = img_resp.content
                front_image_hash = sha256_bytes(front_bytes)

                analyze_resp = requests.post(
                    f"{API_BASE}/analyze",
                    files={"file": ("front.jpg", front_bytes, "image/jpeg")},
                    timeout=60,
                )
                if analyze_resp.status_code != 200:
                    status_box.warning(f"Analyze failed for card_id {row.get('card_id')}: {analyze_resp.text}")
                    fail_count += 1
                    progress.progress(idx / max(total_rows, 1))
                    continue

                analyze_data = analyze_resp.json()
                if "error" in analyze_data:
                    status_box.warning(f"Analyze error for card_id {row.get('card_id')}: {analyze_data['error']}")
                    fail_count += 1
                    progress.progress(idx / max(total_rows, 1))
                    continue

                h = float(analyze_data["horizontal_ratio"])
                v = float(analyze_data["vertical_ratio"])
                edge = float(analyze_data["edge_score"])

                manual_used = parse_bool(row.get("manual_centering_used"))
                manual_h = row.get("front_horizontal_ratio_manual")
                manual_v = row.get("front_vertical_ratio_manual")

                if manual_used and pd.notna(manual_h) and pd.notna(manual_v):
                    try:
                        h = float(manual_h)
                        v = float(manual_v)
                    except Exception:
                        pass

                surface_resp = requests.post(
                    f"{API_BASE}/analyze_surface",
                    files={"file": ("front.jpg", front_bytes, "image/jpeg")},
                    timeout=60,
                )

                row_surface = None
                row_scratch = None
                row_speckle = None
                row_gloss = None
                used_surface_fallback = False

                if surface_resp.status_code == 200:
                    surface_json = surface_resp.json()
                    if "error" not in surface_json:
                        row_surface = surface_json.get("surface_score")
                        row_scratch = surface_json.get("scratch_score")
                        row_speckle = surface_json.get("speckle_score")
                        row_gloss = surface_json.get("gloss_score")

                if row_surface is None:
                    row_surface = 0.12
                    used_surface_fallback = True

                corner_urls = [
                    row.get("corner1_image_url"),
                    row.get("corner2_image_url"),
                    row.get("corner3_image_url"),
                    row.get("corner4_image_url"),
                ]

                fresh_corner_scores = []
                for cu in corner_urls:
                    if pd.isna(cu) or not cu:
                        continue

                    try:
                        corner_img_resp = requests.get(cu, timeout=60)
                        if corner_img_resp.status_code != 200:
                            continue

                        corner_resp = requests.post(
                            f"{API_BASE}/analyze_corner",
                            files={"file": ("corner.jpg", corner_img_resp.content, "image/jpeg")},
                            timeout=60,
                        )
                        if corner_resp.status_code != 200:
                            continue

                        corner_json = corner_resp.json()
                        if "error" in corner_json:
                            continue

                        fresh_corner_scores.append(float(corner_json["corner_score"]))
                    except Exception:
                        continue

                if len(fresh_corner_scores) == 0:
                    corner = float(row.get("corner_score")) if not pd.isna(row.get("corner_score")) else 0.5
                    corner_count_used = 0
                else:
                    corner = min(fresh_corner_scores)
                    corner_count_used = len(fresh_corner_scores)

                raw_grade = compute_base_raw_grade(h, v, corner, edge, float(row_surface))
                piecewise_grade = apply_piecewise_grade(surface_score=float(row_surface), edge_score=edge, horizontal_ratio=h)

                new_grade, grading_path = apply_calibration(
                    raw_grade=raw_grade,
                    surface=row_surface,
                    corner=corner,
                    edge=edge,
                    h=h,
                    v=v,
                    corner_count_used=corner_count_used,
                    used_surface_fallback=used_surface_fallback,
                    manual_centering_used=manual_used,
                )

                confidence = compute_confidence(
                    h=h,
                    v=v,
                    edge=edge,
                    corner=corner,
                    surface=float(row_surface),
                    fitted_grade=new_grade,
                    piecewise_grade=piecewise_grade,
                    used_surface_fallback=used_surface_fallback,
                    corner_count=corner_count_used,
                )

                submit = compute_submit_probability(
                    grade=new_grade,
                    confidence_score=confidence["confidence_score"],
                    surface=float(row_surface),
                    band_spread=confidence["band_spread"],
                )

                current_grade_range = lookup_grade_range(new_grade, range_table)
                new_card_id = str(uuid.uuid4())

                new_data = {
                    "card_id": new_card_id,
                    "model_version": MODEL_VERSION,
                    "player_name": json_safe(row.get("player_name")),
                    "player_name_confidence": json_safe(row.get("player_name_confidence")),
                    "player_name_source": json_safe(row.get("player_name_source")),
                    "manufacturer": json_safe(row.get("manufacturer")),
                    "stock_type": json_safe(row.get("stock_type")),
                    "psa_is_graded": json_safe(row.get("psa_is_graded")),
                    "psa_actual_grade": json_safe(row.get("psa_actual_grade")),
                    "horizontal_ratio": json_safe(h),
                    "vertical_ratio": json_safe(v),
                    "edge_score": json_safe(edge),
                    "corner_score": json_safe(corner),
                    "surface_score": json_safe(row_surface),
                    "scratch_score": json_safe(row_scratch),
                    "speckle_score": json_safe(row_speckle),
                    "gloss_score": json_safe(row_gloss),
                    "raw_formula_grade": json_safe(raw_grade),
                    "calibrated_grade": json_safe(new_grade),
                    "confidence_score": json_safe(confidence["confidence_score"]),
                    "confidence_percent": json_safe(confidence["confidence_percent"]),
                    "confidence_label": json_safe(confidence["confidence_label"]),
                    "agreement_score": json_safe(confidence["agreement_score"]),
                    "threshold_score": json_safe(confidence["boundary_score"]),
                    "data_score": json_safe(confidence["data_score"]),
                    "band_spread": json_safe(None),
                    "submit_probability": json_safe(submit["submit_probability"]),
                    "submit_percent": json_safe(submit["submit_percent"]),
                    "submit_label": json_safe(submit["submit_label"]),
                    "front_image_url": json_safe(row.get("front_image_url")),
                    "back_image_url": json_safe(row.get("back_image_url")),
                    "corner1_image_url": json_safe(row.get("corner1_image_url")),
                    "corner2_image_url": json_safe(row.get("corner2_image_url")),
                    "corner3_image_url": json_safe(row.get("corner3_image_url")),
                    "corner4_image_url": json_safe(row.get("corner4_image_url")),
                    "submitted_by": json_safe(row.get("submitted_by")),
                    "created_at": str(datetime.now()),
                    "manual_centering_used": json_safe(row.get("manual_centering_used")),
                    "front_left_measurement": json_safe(row.get("front_left_measurement")),
                    "front_right_measurement": json_safe(row.get("front_right_measurement")),
                    "front_top_measurement": json_safe(row.get("front_top_measurement")),
                    "front_bottom_measurement": json_safe(row.get("front_bottom_measurement")),
                    "front_horizontal_ratio_manual": json_safe(row.get("front_horizontal_ratio_manual")),
                    "front_vertical_ratio_manual": json_safe(row.get("front_vertical_ratio_manual")),
                    "used_surface_fallback": json_safe(used_surface_fallback),
                    "grade_range_low": json_safe(current_grade_range["range_low"]),
                    "grade_range_high": json_safe(current_grade_range["range_high"]),
                    "grade_band_sample_size": json_safe(current_grade_range["sample_size"]),
                    "grade_band_mae": json_safe(current_grade_range["mae"]),
                    "front_image_hash": json_safe(front_image_hash),
                    "corner_count_used": json_safe(corner_count_used),
                }

                post_resp = requests.post(TABLE_URL, json=new_data, headers=headers, timeout=30)
                if post_resp.status_code not in [200, 201]:
                    status_box.warning(f"Post failed for source card_id {row.get('card_id')}: {post_resp.text}")
                    fail_count += 1
                else:
                    success_count += 1

            except Exception as e:
                status_box.warning(f"Reanalysis exception for source card_id {row.get('card_id')}: {e}")
                fail_count += 1

            status_box.write(
                f"Processed {idx}/{total_rows} | "
                f"source_card_id={row.get('card_id')} | "
                f"path={grading_path if grading_path else 'n/a'} | "
                f"grade={new_grade if new_grade is not None else 'n/a'} | "
                f"confidence={confidence.get('confidence_percent', 'n/a')} | "
                f"submit={submit.get('submit_label', 'n/a')} | "
                f"saved={success_count} | failed={fail_count}"
            )
            progress.progress(idx / max(total_rows, 1))

        st.success(f"True reanalysis completed. Saved {success_count} row(s), failed {fail_count}.")
    st.markdown("</div>", unsafe_allow_html=True)
