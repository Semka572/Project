import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "system.db")

DEFAULT_COURSES = [
    "Mathematics",
    "Physics",
    "Programming",
    "Discrete Structures",
    "Databases",
    "Algorithms",
    "Computer Architecture",
    "Linear Algebra"
]


class Database:
    def __init__(self, path=DB_PATH):
        self.path = path
        self._ensure_init()

    # ---------- INTERNAL ----------
    def _connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_init(self):
        conn = self._connect()
        cur = conn.cursor()

        # USERS
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        );
        """)

        # STUDENTS
        cur.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,

            Ga REAL DEFAULT NULL,
            Ar REAL DEFAULT NULL,
            Cp REAL DEFAULT NULL,
            Ls REAL DEFAULT NULL,
            Ph REAL DEFAULT NULL,

            Gcurrent REAL DEFAULT NULL,
            Gmin REAL DEFAULT NULL,
            Gmax REAL DEFAULT NULL,

            actual REAL DEFAULT NULL,
            last_prediction REAL DEFAULT NULL,

            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        """)

        # STUDENT COURSES
        cur.execute("""
        CREATE TABLE IF NOT EXISTS student_courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            course_name TEXT NOT NULL,
            enabled INTEGER DEFAULT 0,
            grade REAL DEFAULT NULL,
            FOREIGN KEY(student_id) REFERENCES students(id)
        );
        """)

        conn.commit()
        conn.close()

    # ======================================================
    # USERS
    # ======================================================
    def add_user(self, username, password):
        conn = self._connect()
        conn.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, password)
        )
        conn.commit()
        conn.close()

    def get_user(self, username):
        conn = self._connect()
        row = conn.execute(
            "SELECT * FROM users WHERE username=?",
            (username,)
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    # ======================================================
    # STUDENTS
    # ======================================================
    def add_student(self, user_id, name):
        conn = self._connect()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO students (user_id, name) VALUES (?, ?)",
            (user_id, name)
        )
        student_id = cur.lastrowid
        conn.commit()
        conn.close()

        # create default courses
        self.create_missing_student_courses(student_id)

        return student_id

    def list_students(self, user_id):
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM students WHERE user_id=?",
            (user_id,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_student(self, student_id):
        conn = self._connect()
        row = conn.execute(
            "SELECT * FROM students WHERE id=?",
            (student_id,)
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def update_student(self, student_id, **fields):
        if not fields:
            return
        conn = self._connect()
        cur = conn.cursor()
        columns = ", ".join(f"{k}=?" for k in fields)
        values = list(fields.values())
        cur.execute(
            f"UPDATE students SET {columns} WHERE id=?",
            values + [student_id]
        )
        conn.commit()
        conn.close()

    def delete_student(self, student_id):
        conn = self._connect()
        conn.execute("DELETE FROM student_courses WHERE student_id=?", (student_id,))
        conn.execute("DELETE FROM students WHERE id=?", (student_id,))
        conn.commit()
        conn.close()

    # ======================================================
    # COURSES
    # ======================================================
    def create_missing_student_courses(self, student_id):
        conn = self._connect()
        cur = conn.cursor()

        existing = cur.execute(
            "SELECT course_name FROM student_courses WHERE student_id=?",
            (student_id,)
        ).fetchall()
        existing_names = {r[0] for r in existing}

        for c in DEFAULT_COURSES:
            if c not in existing_names:
                cur.execute(
                    "INSERT INTO student_courses (student_id, course_name, enabled) VALUES (?, ?, 0)",
                    (student_id, c)
                )

        conn.commit()
        conn.close()

    def get_student_courses(self, student_id):
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM student_courses WHERE student_id=?",
            (student_id,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def update_course(self, course_id, enabled, grade):
        conn = self._connect()
        conn.execute(
            "UPDATE student_courses SET enabled=?, grade=? WHERE id=?",
            (enabled, grade, course_id)
        )
        conn.commit()
        conn.close()
