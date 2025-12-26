import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join("instance", "app.db")

class HistoryManager:
    def __init__(self):
        self._init_table()

    def _init_table(self):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            timestamp TEXT,
            p_initial REAL,
            p_adjusted REAL,
            alpha REAL,
            beta REAL,
            gamma REAL,
            delta REAL,
            epsilon REAL,
            actual REAL,
            error REAL,
            FOREIGN KEY(student_id) REFERENCES students(id)
        );
        """)

        conn.commit()
        conn.close()

    def add_record(self, student_id, p_initial, p_adjusted, weights, actual):
        error = None
        if actual is not None and p_initial is not None:
            error = actual - p_initial

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        cur.execute("""
        INSERT INTO history (
            student_id, timestamp, p_initial, p_adjusted,
            alpha, beta, gamma, delta, epsilon, actual, error
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            student_id,
            datetime.now().isoformat(),
            p_initial,
            p_adjusted,
            weights["alpha"],
            weights["beta"],
            weights["gamma"],
            weights["delta"],
            weights["epsilon"],
            actual,
            error
        ))

        conn.commit()
        conn.close()

    def get_history(self, student_id):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        rows = cur.execute("""
        SELECT * FROM history
        WHERE student_id=?
        ORDER BY timestamp ASC
        """, (student_id,)).fetchall()

        conn.close()
        return rows


history = HistoryManager()
