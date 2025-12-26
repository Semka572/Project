import os
import pandas as pd
import numpy as np

# Директорії
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
OUT_DIR = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(OUT_DIR, exist_ok=True)

# Базові ваги
WEIGHTS = {
    "alpha": 0.35,
    "beta": 0.25,
    "gamma": 0.20,
    "delta": 0.15,
    "epsilon": 0.05
}
K_CORRECTION = 0.1


def safe_minmax_norm(series, clip=True):
    smin, smax = series.min(), series.max()
    if smin == smax:
        return pd.Series(0.5, index=series.index)
    res = (series - smin) / (smax - smin)
    return res.clip(0,1) if clip else res

def minmax_norm_value(x, xmin, xmax):
    return 0.5 if xmax == xmin else (x - xmin) / (xmax - xmin)

def compute_P(row, w):
    P = (w["alpha"] * row["Ga"] +
         w["beta"]  * row["Ar"] +
         w["gamma"] * row["Cp"] +
         w["delta"] * row["Ls"] +
         w["epsilon"] * row["Ph"])
    return float(np.clip(P, 0.0, 1.0))


students = pd.read_csv(os.path.join(DATA_DIR, "students.csv"))
attendance = pd.read_csv(os.path.join(DATA_DIR, "attendance.csv"))
progress = pd.read_csv(os.path.join(DATA_DIR, "progress.csv"))
lms = pd.read_csv(os.path.join(DATA_DIR, "lms_activity.csv"))

students = students.drop_duplicates(subset=["student_id"]).set_index("student_id")
students = students.fillna(students.mean())
attendance = attendance.fillna(0)
progress = progress.fillna(0)
lms = lms.fillna(0)


att = attendance.copy()
att["w_times_a"] = att["weight"] * att["attendance"]

ar = att.groupby("student_id").agg({"w_times_a": "sum", "weight": "sum"})
ar["Ar"] = ar["w_times_a"] / ar["weight"].replace({0: np.nan})
ar["Ar"] = ar["Ar"].fillna(0)
ar = ar[["Ar"]]


pr = progress.copy()
pr["v_times_c"] = pr["weight"] * pr["progress"]

cp = pr.groupby("student_id").agg({"v_times_c": "sum", "weight": "sum"})
cp["Cp"] = cp["v_times_c"] / cp["weight"].replace({0: np.nan})
cp["Cp"] = cp["Cp"].fillna(0)
cp = cp[["Cp"]]


lms = lms.set_index("student_id")
lms["Ls"] = safe_minmax_norm(lms["activity_score"])


def calc_Ga(row):
    return minmax_norm_value(row["Gcurrent"], row["Gmin"], row["Gmax"])

students["Ga"] = students.apply(calc_Ga, axis=1)
students["Ph"] = students["Ph"].fillna(0.5)


df = students[["Ga", "Ph"]].join(ar, how="left").join(cp, how="left").join(lms[["Ls"]], how="left")
df = df.fillna(0)


df["P_pred_initial"] = df.apply(lambda r: compute_P(r, WEIGHTS), axis=1)


if "actual_outcome" in students.columns:

    merged = df.join(students["actual_outcome"], how="left")
    merged["error"] = merged["actual_outcome"] - merged["P_pred_initial"]

    deltaG = merged["error"].corr(merged["Ga"])
    deltaA = merged["error"].corr(merged["Ar"])

    deltaG = 0 if pd.isna(deltaG) else deltaG
    deltaA = 0 if pd.isna(deltaA) else deltaA

    new_alpha = WEIGHTS["alpha"] * (1 + K_CORRECTION * deltaG)
    new_beta  = WEIGHTS["beta"]  * (1 + K_CORRECTION * deltaA)

    raw = {
        "alpha": new_alpha,
        "beta": new_beta,
        "gamma": WEIGHTS["gamma"],
        "delta": WEIGHTS["delta"],
        "epsilon": WEIGHTS["epsilon"]
    }

    s = sum(raw.values())
    ADJUSTED = {k: raw[k] / s for k in raw}


    df["P_pred_adjusted"] = df.apply(lambda r: compute_P(r, ADJUSTED), axis=1)

else:
    ADJUSTED = None


out_path = os.path.join(OUT_DIR, "predictions.csv")
df.reset_index().to_csv(out_path, index=False)

print("Готово! Результати:", out_path)
print(df.head().to_string())
if ADJUSTED:
    print("\nВідкориговані ваги:")
    for k,v in ADJUSTED.items():
        print(f"{k}: {v:.4f}")
