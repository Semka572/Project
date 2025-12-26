import os
import sqlite3
from typing import List, Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "system.db")

DEFAULT_COURSES = [
    "Mathematics",
    "Probability and Statistics",
    "Programming",
    "Discrete Structures",
    "Databases",
    "Algorithms",
    "Computer Architecture",
    "Linear Algebra",
]


class CourseManager:
    def __init__(self):
        self.db_path = DB_PATH
        self._ensure_tables()
        self._seed_courses()
        self._repair_student_courses()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _ensure_tables(self):
        conn = self._connect()
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            difficulty REAL DEFAULT 2.0
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS student_courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            course_name TEXT NOT NULL,
            enabled INTEGER DEFAULT 0,
            grade REAL DEFAULT NULL,
            course_id INTEGER DEFAULT NULL
        );
        """)

        conn.commit()
        conn.close()

    def _seed_courses(self):
        conn = self._connect()
        cur = conn.cursor()

        existing = {r[0] for r in cur.execute("SELECT name FROM courses").fetchall()}

        for name in DEFAULT_COURSES:
            if name not in existing:
                cur.execute("INSERT INTO courses (name, difficulty) VALUES (?, 2.0)", (name,))

        conn.commit()
        conn.close()

    def _repair_student_courses(self):
        conn = self._connect()
        cur = conn.cursor()

        cur.execute("""
        UPDATE student_courses
        SET course_name = (
            SELECT name FROM courses WHERE courses.id = student_courses.course_id
        )
        WHERE (course_name IS NULL OR TRIM(course_name) = '')
        AND course_id IS NOT NULL;
        """)

        cur.execute("""
        UPDATE student_courses
        SET course_id = (
            SELECT id FROM courses WHERE courses.name = student_courses.course_name
        )
        WHERE (course_id IS NULL OR course_id = 0)
        AND course_name IS NOT NULL
        AND TRIM(course_name) <> '';
        """)

        conn.commit()
        conn.close()

    def create_default_courses(self, student_id: int):
        conn = self._connect()
        cur = conn.cursor()

        existing = {
            r[0] for r in cur.execute(
                "SELECT course_name FROM student_courses WHERE student_id = ?", (student_id,)
            ).fetchall()
        }

        for name in DEFAULT_COURSES:
            if name in existing:
                continue

            row = cur.execute("SELECT id FROM courses WHERE name = ?", (name,)).fetchone()
            cid = row[0] if row else None

            cur.execute("""
            INSERT INTO student_courses (student_id, course_name, enabled, grade, course_id)
            VALUES (?, ?, 0, NULL, ?)
            """, (student_id, name, cid))

        conn.commit()
        conn.close()

        self._repair_student_courses()

    def get_student_courses(self, student_id: int) -> List[Dict[str, Any]]:
        self._repair_student_courses()

        conn = self._connect()
        rows = conn.execute("""
        SELECT
            sc.id,
            sc.student_id,
            sc.course_name,
            sc.course_name AS name,
            sc.enabled,
            sc.grade,
            sc.course_id,
            c.difficulty
        FROM student_courses sc
        LEFT JOIN courses c ON c.id = sc.course_id
        WHERE sc.student_id = ?
        ORDER BY sc.course_name
        """, (student_id,)).fetchall()

        conn.close()
        return [dict(r) for r in rows]

    def update_course(self, course_row_id: int, enabled: int, grade: Optional[float]):
        conn = self._connect()
        conn.execute("""
        UPDATE student_courses
        SET enabled = ?, grade = ?
        WHERE id = ?
        """, (enabled, grade, course_row_id))
        conn.commit()
        conn.close()

        self._repair_student_courses()


course_manager = CourseManager()
