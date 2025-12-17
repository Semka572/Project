# ------------------------------------------------------------
# course_manager.py — manage courses for each student
# ------------------------------------------------------------
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "system.db")


class CourseManager:
    def __init__(self):
        self._ensure_init()

    def _connect(self):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    # ------------------------------------------------------------
    # Create table if not exists
    # ------------------------------------------------------------
    def _ensure_init(self):
        conn = self._connect()
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,

            name TEXT NOT NULL,        -- назва курсу
            enabled INTEGER DEFAULT 0, -- вибрано?
            grade REAL DEFAULT NULL,   -- оцінка користувача

            FOREIGN KEY(student_id) REFERENCES students(id)
        );
        """)

        conn.commit()
        conn.close()

    # ------------------------------------------------------------
    # Create default set of courses for student
    # ------------------------------------------------------------
    def create_default_courses(self, student_id):
        DEFAULT_COURSES = [
            "Course A",
            "Course B",
            "Course C",
            "Course D",
            "Course E"
        ]

        conn = self._connect()
        cur = conn.cursor()

        for c in DEFAULT_COURSES:
            cur.execute("""
            INSERT INTO courses (student_id, name, enabled, grade)
            VALUES (?, ?, 0, NULL)
            """, (student_id, c))

        conn.commit()
        conn.close()

    # ------------------------------------------------------------
    # Load courses for student
    # ------------------------------------------------------------
    def get_student_courses(self, student_id):
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM courses WHERE student_id=?",
            (student_id,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------
    # Update course choice + grade
    # ------------------------------------------------------------
    def update_course(self, cid, enabled, grade):
        conn = self._connect()
        conn.execute("""
        UPDATE courses
        SET enabled=?, grade=?
        WHERE id=?
        """, (enabled, grade, cid))
        conn.commit()
        conn.close()




# Create global instance
course_manager = CourseManager()


