# -----------------------------------------------------
# prediction_engine.py — відповідно до математичної моделі
# -----------------------------------------------------

import math


WEIGHTS = {
    "alpha": 0.35,   # академічні показники
    "beta": 0.25,    # відвідуваність
    "gamma": 0.20,   # прогрес курсів
    "delta": 0.15,   # активність LMS
    "epsilon": 0.05  # історичні дані
}

K = 0.1   # коефіцієнт адаптації


# ---------------------------------------------
# Безпечне перетворення у float
# ---------------------------------------------
def to_float(x):
    try:
        if x is None: 
            return None
        if isinstance(x, (float, int)):
            return float(x)
        x = str(x).replace(",", ".")
        return float(x)
    except:
        return None


# ---------------------------------------------
# Головна функція прогнозу
# student — dict з полями Ga, Ar, Cp, Ls, Ph, actual
# ---------------------------------------------
def compute_prediction(student):

    # Витягуємо параметри
    Ga = to_float(student.get("Ga"))
    Ar = to_float(student.get("Ar"))
    Cp = to_float(student.get("Cp"))
    Ls = to_float(student.get("Ls"))
    Ph = to_float(student.get("Ph"))
    actual = to_float(student.get("actual"))

    # Якщо значення відсутні → 0
    Ga = 0 if Ga is None else Ga
    Ar = 0 if Ar is None else Ar
    Cp = 0 if Cp is None else Cp
    Ls = 0 if Ls is None else Ls
    Ph = 0 if Ph is None else Ph

    # -----------------------------------------------------
    # 1. Базовий прогноз
    # -----------------------------------------------------
    P_initial = (
        WEIGHTS["alpha"] * Ga +
        WEIGHTS["beta"]  * Ar +
        WEIGHTS["gamma"] * Cp +
        WEIGHTS["delta"] * Ls +
        WEIGHTS["epsilon"] * Ph
    )

    P_initial = max(0, min(1, P_initial))

    # -----------------------------------------------------
    # 2. Немає actual → адаптації немає
    # -----------------------------------------------------
    if actual is None:
        return P_initial, None, WEIGHTS.copy()

    # -----------------------------------------------------
    # 3. Обчислення похибки
    # -----------------------------------------------------
    error = actual - P_initial

    # -----------------------------------------------------
    # 4. Корекція ваг згідно дипломної моделі
    # -----------------------------------------------------
    deltaG = error * Ga
    deltaA = error * Ar

    new_alpha = WEIGHTS["alpha"] * (1 + K * deltaG)
    new_beta  = WEIGHTS["beta"]  * (1 + K * deltaA)

    # інші ваги не змінюємо
    new_gamma = WEIGHTS["gamma"]
    new_delta = WEIGHTS["delta"]
    new_epsilon = WEIGHTS["epsilon"]

    # -----------------------------------------------------
    # 5. Нормалізація ваг, щоб сума була = 1
    # -----------------------------------------------------
    s = new_alpha + new_beta + new_gamma + new_delta + new_epsilon

    if s == 0:
        weights_final = WEIGHTS.copy()
    else:
        weights_final = {
            "alpha": new_alpha / s,
            "beta": new_beta / s,
            "gamma": new_gamma / s,
            "delta": new_delta / s,
            "epsilon": new_epsilon / s
        }

    # -----------------------------------------------------
    # 6. Повторний прогноз із оновленими вагами
    # -----------------------------------------------------
    P_adjusted = (
        weights_final["alpha"] * Ga +
        weights_final["beta"]  * Ar +
        weights_final["gamma"] * Cp +
        weights_final["delta"] * Ls +
        weights_final["epsilon"] * Ph
    )

    P_adjusted = max(0, min(1, P_adjusted))

    return P_initial, P_adjusted, weights_final
