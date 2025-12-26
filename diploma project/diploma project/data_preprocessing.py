import numpy as np

# -----------------------------
# Data Preprocessing Module
# -----------------------------
# This module performs all formal steps described in the thesis:
# 1) Cleaning missing values
# 2) Min-Max normalization
# 3) Log transformation for skewed data
# 4) Standardization
# -----------------------------

def safe_to_float(x):
    """
    Safely converts input to float. Returns None if conversion fails.
    """
    try:
        return float(x)
    except:
        return None


def minmax_norm(value, vmin, vmax):
    """
    Performs min-max normalization.
    If vmin == vmax -> returns 0.5 to avoid division by zero.
    """
    if vmin == vmax:
        return 0.5
    return (value - vmin) / (vmax - vmin)


def log_transform(x):
    """
    Applies log(x+1) transformation to reduce right skew.
    Negative values become 0.
    """
    try:
        x = float(x)
        if x < 0:
            x = 0
        return np.log(x + 1)
    except:
        return 0.0


def standardize(value, mean, std):
    """
    Performs standardization: (x - mean) / std.
    If std == 0 → returns 0.
    """
    if std == 0:
        return 0.0
    return (value - mean) / std


def clean_missing(value, default=0.0):
    """
    Replaces None or invalid values with default.
    """
    if value is None:
        return default
    try:
        return float(value)
    except:
        return default


def preprocess_parameter(value, vmin, vmax, mean, std, apply_log=False):
    """
    Full preprocessing pipeline:
    1) Clean
    2) Optional log-transform
    3) Min-max normalization
    4) Standardization

    Returns dict with each stage value.
    """
    v = clean_missing(value)

    if apply_log:
        v = log_transform(v)

    v_norm = minmax_norm(v, vmin, vmax)
    v_std = standardize(v_norm, mean, std)

    return {
        "clean": v,
        "norm": v_norm,
        "std": v_std
    }
