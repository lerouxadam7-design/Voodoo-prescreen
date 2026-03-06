import streamlit as st
import requests
import numpy as np
import pandas as pd
from datetime import datetime
import uuid
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error

# ============================================================
# DESIGN THEME
# ============================================================

st.set_page_config(page_title="Voodoo Sports Grading")

st.markdown("""
<style>
.stApp {
    background: linear-gradient(
        90deg,
        #3F1D6A 0%,
        #522C87 50%,
        #5F3A96 100%
    ) !important;
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

MODEL_VERSION = "v3-linear"

SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
API_BASE = "https://voodoo-centering-api.onrender.com"  # replace

TABLE_URL = f"{SUPABASE_URL}/rest/v1/submissions"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# ============================================================
# AUTHORIZED USERS
# ============================================================

st.markdown("### Access")

user_email = st.text_input("Enter Access Email")

if user_email:

    user_check = requests.get(
        f"{SUPABASE_URL}/rest/v1/authorized_users?email=eq.{user_email}",
        headers=headers
    )

    if user_check.status_code != 200:
        st.error("User lookup failed.")
        st.stop()

    user_data = user_check.json()

    if len(user_data) == 0:
        st.warning("Invite-only beta. Access restricted.")
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

psa_is_graded = st.checkbox("Is this card already PSA graded?")
psa_actual_grade = None

if psa_is_graded:
    psa_actual_grade = st.number_input(
        "Enter PSA Actual Grade",
        min_value=1.0,
        max_value=10.0,
        step=0.5
    )

# ============================================================
# IMAGE UPLOADS
# ============================================================

st.markdown("## Upload Card Images")

full_card_front = st.file_uploader("Full Card - Front", type=["jpg", "jpeg", "png"])
full_card_back = st.file_uploader("Full Card - Back", type=["jpg", "jpeg", "png"])

# ============================================================
# GRADE FUNCTIONS
# ============================================================

def compute_linear_grade(horizontal_ratio, vertical_ratio, edge_score, corner_score):
    centering_raw = (horizontal_ratio + vertical_ratio) / 2
    centering_fixed = 1 - centering_raw

    grade = (
        6.49
        + 4.37 * centering_fixed
        - 0.17 * edge_score
        + 4.92 * corner_score
    )

    return round(max(1, min(10, grade)), 2)

def compute_experimental_grade(horizontal_ratio, vertical_ratio, edge_score, corner_score):
    centering_raw = (horizontal_ratio + vertical_ratio) / 2
    centering_score = 10 - ((1 - centering_raw) * 5)
    edge_scaled = edge_score * 20
    corner_scaled = corner_score * 20
    final = (
        centering_score * 0.4 +
        corner_scaled * 0.4 +
        edge_scaled * 0.2
    )
    return round(max(1, min(10, final)), 2)

# ============================================================
# RUN ANALYSIS
# ============================================================

if st.button("Run Analysis"):

    if full_card_front is None:
        st.error("Front card image required.")
        st.stop()

    response = requests.post(
        f"{API_BASE}/analyze",
        files={"file": full_card_front.getvalue()}
    )

    if response.status_code != 200:
        st.error("Card analysis failed.")
        st.stop()

    result = response.json()

    horizontal_ratio = result["horizontal_ratio"]
    vertical_ratio = result["vertical_ratio"]
    edge_score = result["edge_score"]
    corner_score = result["corner_score"]

    experimental_grade = compute_experimental_grade(
        horizontal_ratio,
        vertical_ratio,
        edge_score,
        corner_score
    )

    calibrated_grade = compute_linear_grade(
        horizontal_ratio,
        vertical_ratio,
        edge_score,
        corner_score
    )

    st.markdown("## Calibrated Grade (Linear v3)")
    st.markdown(f"### {calibrated_grade}")

    st.markdown("## Experimental Grade (v2)")
    st.markdown(f"### {experimental_grade}")

    card_id = str(uuid.uuid4())

    data = {
        "card_id": card_id,
        "model_version": MODEL_VERSION,
        "manufacturer": manufacturer,
        "stock_type": stock_type,
        "psa_is_graded": psa_is_graded,
        "psa_actual_grade": psa_actual_grade,
        "horizontal_ratio": horizontal_ratio,
        "vertical_ratio": vertical_ratio,
        "edge_score": edge_score,
        "corner_score": corner_score,
        "experimental_grade": experimental_grade,
        "calibrated_grade": calibrated_grade,
        "submitted_by": user_email,
        "created_at": str(datetime.now())
    }

    requests.post(TABLE_URL, json=data, headers=headers)
    st.success("Submission saved.")

# ============================================================
# ADMIN DASHBOARD
# ============================================================

if user_role == "admin":

    st.markdown("---")
    st.markdown("## Admin Dashboard")

    analytics = requests.get(TABLE_URL, headers=headers)

    if analytics.status_code == 200:

        df = pd.DataFrame(analytics.json())

        st.write("Total Submissions:", len(df))

        if "psa_actual_grade" in df.columns and "calibrated_grade" in df.columns:

            df_valid = df.dropna(subset=["psa_actual_grade", "calibrated_grade"]).copy()

            if len(df_valid) > 0:

                df_valid.loc[:, "error"] = (
                    df_valid["calibrated_grade"] - df_valid["psa_actual_grade"]
                )

                mae = abs(df_valid["error"]).mean()
                bias = df_valid["error"].mean()

                st.subheader("Linear Model Metrics")
                st.write("MAE:", round(mae, 3))
                st.write("Bias:", round(bias, 3))

        # ----------------------------------------------------
        # GRADIENT BOOSTING TEST
        # ----------------------------------------------------

        st.markdown("---")
        st.subheader("Gradient Boosting (Test Only)")

        df_ml = df.dropna(subset=[
            "psa_actual_grade",
            "horizontal_ratio",
            "vertical_ratio",
            "edge_score",
            "corner_score"
        ]).copy()

        if len(df_ml) > 5:

            df_ml["centering_raw"] = (
                df_ml["horizontal_ratio"] + df_ml["vertical_ratio"]
            ) / 2
            df_ml["centering_fixed"] = 1 - df_ml["centering_raw"]

            X = df_ml[[
                "centering_fixed",
                "edge_score",
                "corner_score"
            ]]
            y = df_ml["psa_actual_grade"]

            gbm = GradientBoostingRegressor(
                n_estimators=300,
                learning_rate=0.05,
                max_depth=3,
                random_state=42
            )

            gbm.fit(X, y)

            preds = gbm.predict(X)

            mae_gbm = mean_absolute_error(y, preds)
            bias_gbm = (preds - y).mean()

            st.write("GBM MAE:", round(mae_gbm, 3))
            st.write("GBM Bias:", round(bias_gbm, 3))

            st.subheader("Feature Importance (GBM)")
            for name, importance in zip(X.columns, gbm.feature_importances_):
                st.write(f"{name}: {round(importance,3)}")

        # ----------------------------------------------------
        # RE-SCORE BUTTON
        # ----------------------------------------------------

        st.markdown("---")
        st.subheader("Model Maintenance")

        if st.button("Re-Score All Cards With Current Linear Model"):

            for _, row in df.iterrows():

                if pd.isna(row.get("horizontal_ratio")):
                    continue

                calibrated_grade = compute_linear_grade(
                    row["horizontal_ratio"],
                    row["vertical_ratio"],
                    row["edge_score"],
                    row["corner_score"]
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
                    "calibrated_grade": calibrated_grade,
                    "submitted_by": user_email,
                    "created_at": str(datetime.now())
                }

                requests.post(TABLE_URL, json=new_data, headers=headers)

            st.success("Re-scored under current model version.")
