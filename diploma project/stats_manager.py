import sqlite3
import os
import numpy as np

# ------------------------------------------------------------
# Stats Manager Module
# ------------------------------------------------------------
# This module calculates and stores parameter statistics used for
# normalization in the prediction model.
# Stats include: min, max, mean, std for each parameter.
# ------------------------------------------------------------

DB_PATH = os.path.join("instance", "app.db")

PARAMETERS = ["Ga", "Ar", "Cp", "Ls", "Ph"]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def compute_stats():
    """
    Reads all students from DB and computes normalization stats for:
    Ga, Ar, Cp, Ls, Ph.

    Returns dict:
    {
        "Ga": {"min":..., "max":..., "mean":..., "std":...},
        "Ar": {...},
        ...
    }
    """

    db = get_db()
    rows = db.execute("SELECT Ga, Ar, Cp, Ls, Ph FROM students").fetchall()

    # If DB empty → default neutral statistics
    if len(rows) == 0:
        return {
            key: {"min": 0, "max": 1, "mean": 0.5, "std": 0.1}
            for key in PARAMETERS
        }

    stats = {}

    for param in PARAMETERS:
        values = []
        for row in rows:
            raw = row[param]
            try:
                values.append(float(raw))
            except:
                continue

        if len(values) == 0:
            stats[param] = {"min": 0, "max": 1, "mean": 0.5, "std": 0.1}
            continue

        arr = np.array(values)
        stats[param] = {
            "min": float(arr.min()),
            "max": float(arr.max()),
            "mean": float(arr.mean()),
            "std": float(arr.std() if arr.std() > 0 else 0.1)
        }

    return stats


def save_stats(stats, path="instance/stats.npy"):
    """
    Saves computed statistics to a .npy file.
    """
    np.save(path, stats, allow_pickle=True)


def load_stats(path="instance/stats.npy"):
    """
    Loads saved statistics.
    If file missing → returns default.
    """
    if not os.path.exists(path):
        return {
            key: {"min": 0, "max": 1, "mean": 0.5, "std": 0.1}
            for key in PARAMETERS
        }

    stats = np.load(path, allow_pickle=True).item()
    return stats
