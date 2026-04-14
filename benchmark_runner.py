import requests
import pandas as pd
import numpy as np

# ============================
# CONFIG
# ============================

SUPABASE_URL = "https://nnowtzpkldfrkixeonau.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5ub3d0enBrbGRmcmtpeGVvbmF1Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MTk3NDIzMiwiZXhwIjoyMDg3NTUwMjMyfQ.7XY3evntb9FOUHqEMeT8uuaKgAsB98jfay4FlPhvknA"
API_BASE = "https://voodoo-centering-api.onrender.com"

TABLE_URL = f"{SUPABASE_URL}/rest/v1/submissions"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
}

# ============================
# LOAD BENCHMARK DATA
# ============================

def load_data():
    resp = requests.get(TABLE_URL, headers=headers)
    df = pd.DataFrame(resp.json())

    # Only PSA graded rows
    df = df[df["psa_actual_grade"].notna()].copy()

    return df

# ============================
# GRADE MODEL (same as app)
# ============================

def compute_grade(h, v, edge, corner, surface):
    v_good = 1.0 - float(v)
    surface_bad = min(float(surface), 0.16)

    grade = (
        8.35
        + 0.25 * v_good
        - 0.47 * float(corner)
        - 0.94 * float(edge)
        + 32.0 * surface_bad
        - 300.0 * (surface_bad ** 2)
    )

    if grade >= 9.0:
        grade += 0.15
    elif grade <= 7.5:
        grade -= 0.15

    return round(max(1.0, min(10.0, grade)), 2)

# ============================
# MAIN LOOP
# ============================

results = []

df = load_data()

for _, row in df.iterrows():
    try:
        front_url = row["front_image_url"]

        img = requests.get(front_url).content

        # Analyze
        r = requests.post(
            f"{API_BASE}/analyze",
            files={"file": ("img.jpg", img, "image/jpeg")},
        ).json()

        s = requests.post(
            f"{API_BASE}/analyze_surface",
            files={"file": ("img.jpg", img, "image/jpeg")},
        ).json()

        if "error" in r:
            continue

        h = r["horizontal_ratio"]
        v = r["vertical_ratio"]
        edge = r["edge_score"]
        corner = r["corner_score"] if "corner_score" in r else row["corner_score"]
        surface = s.get("surface_score", 0.12)

        grade = compute_grade(h, v, edge, corner, surface)

        psa = float(row["psa_actual_grade"])
        error = grade - psa

        results.append({
            "card_id": row["card_id"],
            "psa": psa,
            "v10_6_grade": grade,
            "error": error,
            "abs_error": abs(error)
        })

        print(f"Processed {row['card_id']} → {grade}")

    except Exception as e:
        print("Error:", e)

# ============================
# RESULTS
# ============================

out = pd.DataFrame(results)

print("\n=== RESULTS ===")
print("MAE:", round(out["abs_error"].mean(), 3))
print("Bias:", round(out["error"].mean(), 3))
print("Within 0.5:", round((out["abs_error"] <= 0.5).mean(), 3))
print("Within 1.0:", round((out["abs_error"] <= 1.0).mean(), 3))

out.to_csv("benchmark_results.csv", index=False)
print("\nSaved to benchmark_results.csv")
