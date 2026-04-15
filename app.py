# ==============================
# VOODOO SPORTS GRADING APP
# ==============================

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
# CONFIG
# ============================================================

MODEL_VERSION = "v9.6-ui + v9.7-confidence + surface-calibrated"
API_BASE = "https://voodoo-centering-api.onrender.com"

SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]

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

# ============================================================
# SESSION STATE
# ============================================================

if "analysis_complete" not in st.session_state:
    st.session_state.analysis_complete = False

if "analysis_payload" not in st.session_state:
    st.session_state.analysis_payload = None

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


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_ratio(a, b):
    if a <= 0 or b <= 0:
        return 0.5
    return min(a, b) / max(a, b)


# ============================================================
# CENTERING + SUBGRADES
# ============================================================

def centering_psa_grade(h, v):
    worst = min(h, v)
    if worst >= 0.90:
        return 10
    elif worst >= 0.80:
        return 9
    elif worst >= 0.70:
        return 8
    return 7


def remap_corner(c):
    return np.sqrt(max(0, min(1, c)))


# ============================================================
# SURFACE CALIBRATION
# ============================================================

def compute_surface_scale_from_history(df):
    if df is None or df.empty:
        return 0.63, 0

    if "psa_actual_grade" not in df.columns:
        return 0.63, 0

    work = df.dropna(subset=["psa_actual_grade", "surface_score"])
    if len(work) < 10:
        return 0.63, len(work)

    # simple calibration based on bias
    bias = (work["calibrated_grade"] - work["psa_actual_grade"]).mean()

    # adjust scale slightly
    scale = 0.63
    if bias < -0.5:
        scale = 0.65
    elif bias > 0.5:
        scale = 0.58

    return scale, len(work)


def apply_surface_scale(surface, scale):
    return surface * scale


# ============================================================
# GRADE MODEL
# ============================================================

def compute_fitted_grade(h, v, corner, edge, surface):
    v_good = 1.0 - v

    grade = (
        8.35
        + 0.25 * v_good
        - 0.47 * corner
        - 0.94 * edge
        + 38.67 * surface
        - 350.94 * (surface ** 2)
    )

    return round(max(1.0, min(10.0, grade)), 2)


# ============================================================
# CONFIDENCE (v9.7)
# ============================================================

def compute_confidence(h, v, edge, corner, surface, fallback, corner_count):
    spread = max([h, v]) - min([h, v])
    agreement = max(0, 1 - spread / 5.5)

    threshold = 0.5  # simplified
    data_score = 1.0

    if fallback:
        data_score -= 0.12
    if corner_count < 2:
        data_score -= 0.20

    conf = (
        0.50 * agreement +
        0.30 * threshold +
        0.20 * data_score
    )

    conf = max(0, min(1, conf))
    percent = round(conf * 100, 1)

    if percent >= 75:
        label = "High"
    elif percent >= 55:
        label = "Moderate"
    else:
        label = "Low"

    return {
        "confidence_score": conf,
        "confidence_percent": percent,
        "confidence_label": label,
    }


# ============================================================
# SUBMIT RULES (v9.7)
# ============================================================

def compute_submit(grade, confidence):
    if grade >= 9.4:
        return "Strong Submit"
    elif grade >= 9.0:
        return "Submit"
    elif grade >= 8.6 and confidence >= 58:
        return "Risky"
    return "Do Not Submit"


# ============================================================
# UI
# ============================================================

st.title("VOODOO SPORTS GRADING")

user_email = st.text_input("Enter Access Email")

player_name_input = st.text_input("Player Name")
manufacturer = st.text_input("Manufacturer")

front = st.file_uploader("Front Image")
back = st.file_uploader("Back Image")

corner1 = st.file_uploader("Corner 1")
corner2 = st.file_uploader("Corner 2")

# ============================================================
# ANALYSIS
# ============================================================

if st.button("Run Analysis"):
    if not front:
        st.error("Front required")
        st.stop()

    front_bytes = front.getvalue()

    r = requests.post(
        f"{API_BASE}/analyze",
        files={"file": ("front.jpg", front_bytes, "image/jpeg")}
    )

    data = r.json()

    h = data["horizontal_ratio"]
    v = data["vertical_ratio"]
    edge = data["edge_score"]

    # surface
    sr = requests.post(
        f"{API_BASE}/analyze_surface",
        files={"file": ("front.jpg", front_bytes, "image/jpeg")}
    )

    surface = sr.json().get("surface_score", 0.12)
    used_surface_fallback = surface is None

    # apply calibration
    scale, sample_size = compute_surface_scale_from_history(pd.DataFrame())
    surface = apply_surface_scale(surface, scale)

    # corners
    corner_scores = []
    for c in [corner1, corner2]:
        if c:
            cr = requests.post(
                f"{API_BASE}/analyze_corner",
                files={"file": ("corner.jpg", c.getvalue(), "image/jpeg")}
            )
            corner_scores.append(cr.json()["corner_score"])

    corner = min(corner_scores) if corner_scores else 0.5

    # grade
    grade = compute_fitted_grade(h, v, corner, edge, surface)

    confidence = compute_confidence(
        h, v, edge, corner, surface,
        used_surface_fallback,
        len(corner_scores)
    )

    submit = compute_submit(grade, confidence["confidence_percent"])

    st.session_state.analysis_payload = {
        "grade": grade,
        "confidence": confidence,
        "submit": submit,
        "surface_scale": scale,
    }

    st.session_state.analysis_complete = True

# ============================================================
# RESULTS
# ============================================================

if st.session_state.analysis_complete:
    result = st.session_state.analysis_payload

    st.write("Grade:", result["grade"])
    st.write("Confidence:", result["confidence"]["confidence_percent"])
    st.write("Submit:", result["submit"])
    st.write("Surface Scale:", result["surface_scale"])

# ============================================================
# RESCORE (WITH MANUAL CENTERING)
# ============================================================

if st.button("True Reanalyze Saved Cards"):
    resp = requests.get(TABLE_URL, headers=headers)
    df = pd.DataFrame(resp.json())

    for _, row in df.iterrows():

        front_url = row.get("front_image_url")
        if not front_url:
            continue

        img = requests.get(front_url).content

        r = requests.post(
            f"{API_BASE}/analyze",
            files={"file": ("front.jpg", img, "image/jpeg")}
        )

        data = r.json()
        h = data["horizontal_ratio"]
        v = data["vertical_ratio"]
        edge = data["edge_score"]

        # APPLY MANUAL CENTERING
        if row.get("manual_centering_used"):
            if pd.notna(row.get("front_horizontal_ratio_manual")):
                h = float(row["front_horizontal_ratio_manual"])
            if pd.notna(row.get("front_vertical_ratio_manual")):
                v = float(row["front_vertical_ratio_manual"])

        sr = requests.post(
            f"{API_BASE}/analyze_surface",
            files={"file": ("front.jpg", img, "image/jpeg")}
        )

        surface = sr.json().get("surface_score", 0.12)

        # apply scale
        scale, _ = compute_surface_scale_from_history(df)
        surface = apply_surface_scale(surface, scale)

        grade = compute_fitted_grade(h, v, 0.5, edge, surface)

        confidence = compute_confidence(h, v, edge, 0.5, surface, False, 2)
        submit = compute_submit(grade, confidence["confidence_percent"])

        payload = {
            "card_id": str(uuid.uuid4()),
            "calibrated_grade": grade,
            "confidence_percent": confidence["confidence_percent"],
            "submit_label": submit,
            "created_at": str(datetime.now())
        }

        requests.post(TABLE_URL, json=payload, headers=headers)

    st.success("Rescore complete")
