# ------------------------------------------------------------
# prediction_engine.py — FIXED (proper normalization)
# ------------------------------------------------------------
from __future__ import annotations

import numpy as np

# Initial diploma weights
WEIGHTS = {
    "alpha": 0.35,   # Ga
    "beta": 0.25,    # Ar
    "gamma": 0.20,   # Cp
    "delta": 0.15,   # Ls
    "epsilon": 0.05  # Ph
}

K = 0.9   # correction factor


def safe_float(x, default=None):
    try:
        if x is None or x == "":
            return default
        return float(x)
    except Exception:
        return default


def to_01(x, default=0.0) -> float:
    """
    Normalize to [0..1].
    Accepts either:
      - already normalized 0..1
      - percent-like 0..100 (auto /100 if > 1.5)
    """
    v = safe_float(x, default)
    if v is None:
        v = default

    # heuristic: treat values > 1.5 as "0..100 scale"
    if v > 1.5:
        v = v / 100.0

    return float(np.clip(v, 0.0, 1.0))


def compute_Ga(student) -> float | None:
    """Normalized academic performance (Diploma definition)."""
    gcur = safe_float(student.get("Gcurrent"))
    gmin = safe_float(student.get("Gmin"))
    gmax = safe_float(student.get("Gmax"))

    if gcur is None or gmin is None or gmax is None:
        return None
    if gmax == gmin:
        return None

    ga = (gcur - gmin) / (gmax - gmin)
    return float(np.clip(ga, 0.0, 1.0))


def compute_Ar(student, courses) -> float:
    """
    Attendance:
      - if student has Ar field => use it (preferred)
      - else fallback to enabled courses ratio (legacy)
    """
    if student is not None and student.get("Ar") not in (None, ""):
        return to_01(student.get("Ar"), default=0.0)

    # fallback legacy
    if not courses:
        return 0.0
    enabled = sum(1 for c in courses if int(c.get("enabled", 0)) == 1)
    return float(enabled / len(courses))


def compute_Cp(courses) -> float:
    """Course performance: mean(grade/100) for enabled courses."""
    grades = []
    for c in courses or []:
        if int(c.get("enabled", 0)) != 1:
            continue
        g = safe_float(c.get("grade"))
        if g is None:
            continue
        grades.append(g / 100.0)

    if not grades:
        return 0.0

    cp = sum(grades) / len(grades)
    return float(np.clip(cp, 0.0, 1.0))


def predict(student, courses):
    # --------------------------------------------------------
    # 1) Extract + normalize factors to [0..1]
    # --------------------------------------------------------
    Ga = compute_Ga(student)
    Cp = compute_Cp(courses)
    Ar = compute_Ar(student, courses)

    # Ls/Ph можуть приходити як 0..1 або 0..100 => нормалізуємо
    Ls = to_01(student.get("Ls"), default=0.0)
    Ph = to_01(student.get("Ph"), default=0.0)

    # actual теж може бути 0..1 або 0..100
    actual = safe_float(student.get("actual"))
    actual_n = None if actual is None else to_01(actual, default=0.0)

    # fallback for Ga if missing
    if Ga is None:
        Ga = Cp

    # safety clamp (на випадок NaN)
    Ga = float(np.clip(Ga, 0.0, 1.0))
    Ar = float(np.clip(Ar, 0.0, 1.0))
    Cp = float(np.clip(Cp, 0.0, 1.0))
    # Ls, Ph already clamped

    # --------------------------------------------------------
    # 2) Compute INITIAL probability
    # --------------------------------------------------------
    P_initial = (
        WEIGHTS["alpha"] * Ga +
        WEIGHTS["beta"]  * Ar +
        WEIGHTS["gamma"] * Cp +
        WEIGHTS["delta"] * Ls +
        WEIGHTS["epsilon"] * Ph
    )
    P_initial = float(np.clip(P_initial, 0.0, 1.0))

    # No correction possible
    if actual_n is None:
        return P_initial, None, WEIGHTS

    # --------------------------------------------------------
    # 3) Error for correction (actual - predicted)
    # --------------------------------------------------------
    error = actual_n - P_initial

    # Diploma adaptive rules:
    # (залишаємо вашу ідею, але вже на нормалізованих значеннях)
    deltaG = error * Ga * abs(error)
    deltaA = error * Ar * abs(error)

    # --------------------------------------------------------
    # 4) Apply correction for α and β
    # --------------------------------------------------------
    new_alpha = WEIGHTS["alpha"] * (1 + K * deltaG)
    new_beta  = WEIGHTS["beta"]  * (1 + K * deltaA)

    updated = {
        "alpha": new_alpha,
        "beta": new_beta,
        "gamma": WEIGHTS["gamma"],
        "delta": WEIGHTS["delta"],
        "epsilon": WEIGHTS["epsilon"],
    }

    # Normalize weights (sum = 1)
    s = sum(updated.values())
    if s == 0:
        updated = dict(WEIGHTS)
        s = sum(updated.values())

    for k in updated:
        updated[k] /= s

    # --------------------------------------------------------
    # 5) Compute ADJUSTED probability
    # --------------------------------------------------------
    P_adjusted = (
        updated["alpha"] * Ga +
        updated["beta"]  * Ar +
        updated["gamma"] * Cp +
        updated["delta"] * Ls +
        updated["epsilon"] * Ph
    )
    P_adjusted = float(np.clip(P_adjusted, 0.0, 1.0))

    return P_initial, P_adjusted, updated
