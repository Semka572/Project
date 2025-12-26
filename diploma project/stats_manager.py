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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "system.db")

PARAMETERS = ["Ga", "Ar", "Cp", "Ls", "Ph"]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def compute_stats():
    db = get_db()
    rows = db.execute("SELECT Ga, Ar, Cp, Ls, Ph FROM students").fetchall()
    db.close()

    if len(rows) == 0:
        return {key: {"min": 0, "max": 1, "mean": 0.5, "std": 0.1} for key in PARAMETERS}

    stats = {}

    for param in PARAMETERS:
        values = []
        for row in rows:
            raw = row[param]
            try:
                values.append(float(raw))
            except Exception:
                continue

        if len(values) == 0:
            stats[param] = {"min": 0, "max": 1, "mean": 0.5, "std": 0.1}
            continue

        arr = np.array(values, dtype=float)
        s = float(arr.std())
        stats[param] = {
            "min": float(arr.min()),
            "max": float(arr.max()),
            "mean": float(arr.mean()),
            "std": float(s if s > 0 else 0.1),
        }

    return stats


def save_stats(stats, path=None):
    if path is None:
        path = os.path.join(BASE_DIR, "stats.npy")
    np.save(path, stats, allow_pickle=True)


def load_stats(path=None):
    if path is None:
        path = os.path.join(BASE_DIR, "stats.npy")

    if not os.path.exists(path):
        return {key: {"min": 0, "max": 1, "mean": 0.5, "std": 0.1} for key in PARAMETERS}

    stats = np.load(path, allow_pickle=True).item()
    return stats
