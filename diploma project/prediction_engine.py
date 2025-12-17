# ------------------------------------------------------------
# prediction_engine.py — Final version with course integration
# ------------------------------------------------------------

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
        return float(x)
    except:
        return default


def compute_Ga(student):
    """Normalized academic performance (Diploma definition)."""
    gcur = safe_float(student.get("Gcurrent"))
    gmin = safe_float(student.get("Gmin"))
    gmax = safe_float(student.get("Gmax"))

    if gcur is None or gmin is None or gmax is None:
        # fallback: if missing – approximate Ga using Cp
        return None

    if gmax == gmin:
        return None

    return (gcur - gmin) / (gmax - gmin)


def compute_Ar(courses):
    """Attendance: number of enabled courses / total."""
    if not courses:
        return 0
    
    enabled = sum(1 for c in courses if c["enabled"])
    return enabled / len(courses)


def compute_Cp(courses):
    """Course performance: mean(grade/100)."""
    grades = [
        safe_float(c["grade"]) / 100
        for c in courses
        if c["enabled"] and safe_float(c["grade"]) is not None
    ]

    if not grades:
        return 0

    return sum(grades) / len(grades)


def predict(student, courses):
    # --------------------------------------------------------
    # 1. Extract factors
    # --------------------------------------------------------
    Ga = compute_Ga(student)
    Ar = compute_Ar(courses)
    Cp = compute_Cp(courses)
    Ls = safe_float(student.get("Ls"), 0)
    Ph = safe_float(student.get("Ph"), 0)
    actual = safe_float(student.get("actual"))

    # fallback for Ga
    if Ga is None:
        Ga = Cp

    # --------------------------------------------------------
    # 2. Compute INITIAL P using diploma formula
    # --------------------------------------------------------
    P_initial = (
        WEIGHTS["alpha"] * Ga +
        WEIGHTS["beta"]  * Ar +
        WEIGHTS["gamma"] * Cp +
        WEIGHTS["delta"] * Ls +
        WEIGHTS["epsilon"] * Ph
    )
    P_initial = float(np.clip(P_initial, 0, 1))

    # No correction possible
    if actual is None:
        return P_initial, None, WEIGHTS

    # --------------------------------------------------------
    # 3. Error for correction
    # --------------------------------------------------------
    error = actual - P_initial

    # Diploma adaptive rules:
    deltaG = error * Ga * abs(error)
    deltaA = error * Ar * abs(error)

    # --------------------------------------------------------
    # 4. Apply correction for α and β
    # --------------------------------------------------------
    new_alpha = WEIGHTS["alpha"] * (1 + K * deltaG)
    new_beta  = WEIGHTS["beta"]  * (1 + K * deltaA)

    updated = {
        "alpha": new_alpha,
        "beta": new_beta,
        "gamma": WEIGHTS["gamma"],
        "delta": WEIGHTS["delta"],
        "epsilon": WEIGHTS["epsilon"]
    }

    # Normalize weights (sum = 1)
    s = sum(updated.values())
    for k in updated:
        updated[k] /= s

    # --------------------------------------------------------
    # 5. Compute ADJUSTED probability
    # --------------------------------------------------------
    P_adjusted = (
        updated["alpha"] * Ga +
        updated["beta"]  * Ar +
        updated["gamma"] * Cp +
        updated["delta"] * Ls +
        updated["epsilon"] * Ph
    )

    P_adjusted = float(np.clip(P_adjusted, 0, 1))

    return P_initial, P_adjusted, updated
