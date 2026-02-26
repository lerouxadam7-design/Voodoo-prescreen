import streamlit as st
import numpy as np
import requests
from datetime import datetime
from PIL import Image
import uuid
import pandas as pd

# ===============================
# CENTERING ENGINE CLASSES
# ===============================

    def __init__(self):
        self.glare = GlareDetector()
        self.confidence = ConfidenceScorer()

    def detect_card(self, image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 75, 200)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        largest = max(contours, key=cv2.contourArea)
        peri = cv2.arcLength(largest, True)
        approx = cv2.approxPolyDP(largest, 0.02 * peri, True)
        if len(approx) != 4:
            raise ValueError("Card detection failed")
        pts = approx.reshape(4, 2).astype("float32")
        return self.order_points(pts)

    def warp_card(self, image, pts):
        (tl, tr, br, bl) = pts
        widthA = np.linalg.norm(br - bl)
        widthB = np.linalg.norm(tr - tl)
        maxWidth = int(max(widthA, widthB))
        heightA = np.linalg.norm(tr - br)
        heightB = np.linalg.norm(tl - bl)
        maxHeight = int(max(heightA, heightB))
        dst = np.array([
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1]], dtype="float32")
        M = cv2.getPerspectiveTransform(pts, dst)
        return cv2.warpPerspective(image, M, (maxWidth, maxHeight))

    def detect_borders(self, warped):
        h, w, _ = warped.shape
        band_w = int(w * 0.15)
        band_h = int(h * 0.15)
        bands = [
            warped[:, :band_w],
            warped[:, w - band_w:],
            warped[:band_h, :],
            warped[h - band_h:, :]
        ]
        borders = []
        for idx, band in enumerate(bands):
            gray = cv2.cvtColor(band, cv2.COLOR_BGR2GRAY)
            glare_mask = self.glare.detect_glare_mask(band)
            gray = self.glare.inpaint(gray, glare_mask)
            edges = cv2.Canny(gray, 50, 150)
            lines = cv2.HoughLinesP(
                edges, 1, np.pi / 180, threshold=80,
                minLineLength=int((h if idx < 2 else w) * 0.6),
                maxLineGap=10
            )
            if lines is None:
                borders.append(None)
                continue
            lines = lines[:, 0, :]
            best_line = max(lines, key=lambda l: abs(l[1] - l[3]))
            if idx == 0:
                borders.append(best_line[0])
            elif idx == 1:
                borders.append(w - band_w + best_line[0])
            elif idx == 2:
                borders.append(best_line[1])
            else:
                borders.append(h - band_h + best_line[1])
        return borders

    def calculate_centering(self, warped, borders):
        if None in borders:
            return None
        h, w, _ = warped.shape
        left, right, top, bottom = borders
        left_border = left
        right_border = w - right
        top_border = top
        bottom_border = h - bottom
        h_ratio = min(left_border, right_border) / max(left_border, right_border)
        v_ratio = min(top_border, bottom_border) / max(top_border, bottom_border)
        return h_ratio, v_ratio

    def analyze_array(self, image_array):
        pts = self.detect_card(image_array)
        warped = self.warp_card(image_array, pts)
        borders = self.detect_borders(warped)
        ratios = self.calculate_centering(warped, borders)
        if ratios is None:
            return {"error": "Border detection failed"}
        h_ratio, v_ratio = ratios
        return {
            "horizontal_ratio": h_ratio,
            "vertical_ratio": v_ratio
        }

    def order_points(self, pts):
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        return rect


centering_engine = ProfessionalCenteringEngineV68()

# ===============================
# CONFIG
# ===============================

MODEL_VERSION = "v1.4-beta"
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
TABLE_URL = f"{SUPABASE_URL}/rest/v1/submissions"
STORAGE_URL = f"{SUPABASE_URL}/storage/v1/object"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# ===============================
# UI
# ===============================

AUTHORIZED_USERS = ["Adaml"]
user_email = st.text_input("Enter Access Email")

if user_email not in AUTHORIZED_USERS:
    st.warning("Invite-only beta. Access restricted.")
    st.stop()

st.set_page_config(page_title="Voodoo Sports Grading")
st.title("VOODOO SPORTS GRADING")
st.subheader("PSA Pre-Screen Analyzer")

front = st.file_uploader("Upload Front Image", type=["jpg", "png"])
back = st.file_uploader("Upload Back Image", type=["jpg", "png"])

manufacturer = st.text_input("Manufacturer")
stock_type = st.selectbox("Stock Type", ["paper", "chrome", "refractor", "foil", "other"])

psa10 = st.number_input("PSA 10 Value", value=100.0)
psa9 = st.number_input("PSA 9 Value", value=50.0)
psa8 = st.number_input("PSA 8 Value", value=20.0)
fee = st.number_input("Grading Fee", value=25.0)

psa_is_graded = st.checkbox("Is this card already PSA graded?")
psa_actual_grade = st.number_input("Enter PSA Actual Grade", min_value=1.0, max_value=10.0, step=0.5) if psa_is_graded else None

corners_input = st.slider("Corners (1-10)", 1, 10, 9)
edges_input = st.slider("Edges (1-10)", 1, 10, 9)
surface_input = st.slider("Surface (1-10)", 1, 10, 9)

# ===============================
# RUN ANALYSIS
# ===============================

if st.button("Run Pre-Screen Analysis"):

    if not front or not back:
        st.error("Upload both images.")
        st.stop()

    weighted_grade = (
        auto_centering_score * 0.35
        + corners_input * 0.25
        + edges_input * 0.20
        + surface_input * 0.20
    )

    mean = round(weighted_grade, 2)

    if mean > 9:
        mean = 9 + (mean - 9) * 0.4

    st.write("Auto Centering Score:", auto_centering_score)
    st.write("Final Predicted Grade:", round(mean, 2))
