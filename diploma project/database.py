# database.py
import os
import sqlite3
from typing import Any, Dict, List, Optional, Sequence, Tuple

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "system.db")

DEFAULT_COURSES = [
    "Mathematics",
    "Physics",
    "Programming",
    "Discrete Structures",
    "Databases",
    "Algorithms",
    "Computer Architecture",
    "Linear Algebra",
]


class Database:
    def __init__(self, path: str = DB_PATH):
        # абсолютний шлях, щоб не було різних working directory
        self.path = os.path.abspath(path)
        self._ensure_init()

    # ---------------- INTERNAL ----------------
    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _fetchone(self, sql: str, params: Sequence[Any] = ()) -> Optional[Dict[str, Any]]:
        conn = self._connect()
        try:
            row = conn.execute(sql, params).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def _fetchall(self, sql: str, params: Sequence[Any] = ()) -> List[Dict[str, Any]]:
        conn = self._connect()
        try:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def _execute(self, sql: str, params: Sequence[Any] = ()) -> int:
        conn = self._connect()
        try:
            cur = conn.execute(sql, params)
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def _executemany(self, sql: str, seq_of_params: Sequence[Sequence[Any]]) -> None:
        conn = self._connect()
        try:
            conn.executemany(sql, seq_of_params)
            conn.commit()
        finally:
            conn.close()

    # ---------------- INIT ----------------
    def _ensure_init(self) -> None:
        """
        Always ensures required tables exist. Safe on empty/old DB.
        """
        conn = self._connect()
        try:
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

                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """)

            # COURSES CATALOG (global)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                difficulty REAL NOT NULL DEFAULT 2.0
            );
            """)

            # student_courses (per-student)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS student_courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                course_name TEXT NOT NULL,
                enabled INTEGER DEFAULT 0,
                grade REAL DEFAULT NULL,
                course_id INTEGER DEFAULT NULL,
                FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE,
                FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE SET NULL
            );
            """)

            # prerequisites
            cur.execute("""
            CREATE TABLE IF NOT EXISTS course_prerequisites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                prerequisite_course_id INTEGER NOT NULL,
                UNIQUE(course_id, prerequisite_course_id),
                FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE,
                FOREIGN KEY(prerequisite_course_id) REFERENCES courses(id) ON DELETE CASCADE
            );
            """)

            # trajectory plan
            cur.execute("""
            CREATE TABLE IF NOT EXISTS trajectory_plan (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                semester TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'planned',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(student_id, course_id, semester),
                FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE,
                FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE
            );
            """)

            conn.commit()
        finally:
            conn.close()

        # seed catalog & sync
        self.ensure_catalog_ready()

    # ---------------- PUBLIC HELPERS ----------------
    def ensure_catalog_ready(self) -> None:
        self._seed_courses_catalog()
        self._sync_student_courses_course_ids()

    def _seed_courses_catalog(self) -> None:
        existing = self._fetchall("SELECT name FROM courses;")
        existing_names = {r["name"] for r in existing}

        to_insert = [(name, 2.0) for name in DEFAULT_COURSES if name not in existing_names]
        if to_insert:
            self._executemany("INSERT INTO courses(name, difficulty) VALUES (?, ?);", to_insert)

    def _sync_student_courses_course_ids(self) -> None:
        self._execute("""
        UPDATE student_courses
        SET course_id = (SELECT id FROM courses WHERE courses.name = student_courses.course_name)
        WHERE (course_id IS NULL OR course_id = 0)
          AND course_name IN (SELECT name FROM courses);
        """)

    # ======================================================
    # USERS
    # ======================================================
    def add_user(self, username: str, password: str) -> int:
        return self._execute(
            "INSERT INTO users (username, password) VALUES (?, ?);",
            (username, password),
        )

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        return self._fetchone("SELECT * FROM users WHERE username = ?;", (username,))

    # ======================================================
    # STUDENTS
    # ======================================================
    def add_student(self, user_id: int, name: str) -> int:
        sid = self._execute("INSERT INTO students (user_id, name) VALUES (?, ?);", (user_id, name))
        self.create_missing_student_courses(sid)
        self.ensure_catalog_ready()
        return sid

    def list_students(self, user_id: int) -> List[Dict[str, Any]]:
        return self._fetchall("SELECT * FROM students WHERE user_id = ?;", (user_id,))

    def get_student(self, student_id: int) -> Optional[Dict[str, Any]]:
        return self._fetchone("SELECT * FROM students WHERE id = ?;", (student_id,))

    def update_student(self, student_id: int, **fields: Any) -> None:
        if not fields:
            return
        columns = ", ".join(f"{k}=?" for k in fields.keys())
        values = list(fields.values())
        self._execute(f"UPDATE students SET {columns} WHERE id = ?;", values + [student_id])

    def delete_student(self, student_id: int) -> None:
        self._execute("DELETE FROM student_courses WHERE student_id = ?;", (student_id,))
        self._execute("DELETE FROM trajectory_plan WHERE student_id = ?;", (student_id,))
        self._execute("DELETE FROM students WHERE id = ?;", (student_id,))

    # ======================================================
    # STUDENT COURSES
    # ======================================================
    def create_missing_student_courses(self, student_id: int) -> None:
        existing = self._fetchall(
            "SELECT course_name FROM student_courses WHERE student_id = ?;",
            (student_id,),
        )
        existing_names = {r["course_name"] for r in existing}

        inserts: List[Tuple[int, str, int]] = []
        for cname in DEFAULT_COURSES:
            if cname in existing_names:
                continue
            row = self._fetchone("SELECT id FROM courses WHERE name = ?;", (cname,))
            course_id = int(row["id"]) if row else None
            inserts.append((student_id, cname, course_id))

        if inserts:
            self._executemany(
                "INSERT INTO student_courses (student_id, course_name, enabled, grade, course_id) VALUES (?, ?, 0, NULL, ?);",
                inserts,
            )

    def get_student_courses(self, student_id: int) -> List[Dict[str, Any]]:
        return self._fetchall("""
            SELECT sc.*, c.difficulty as difficulty
            FROM student_courses sc
            LEFT JOIN courses c ON c.id = sc.course_id
            WHERE sc.student_id = ?
            ORDER BY sc.course_name;
        """, (student_id,))

    def update_course(self, course_row_id: int, enabled: int, grade: Optional[float]) -> None:
        self._execute(
            "UPDATE student_courses SET enabled = ?, grade = ? WHERE id = ?;",
            (enabled, grade, course_row_id),
        )

    # ======================================================
    # CATALOG + PREREQUISITES + PLAN
    # ======================================================
    def get_all_courses(self) -> List[Dict[str, Any]]:
        return self._fetchall("SELECT * FROM courses ORDER BY name;")

    def get_prerequisites(self, course_id: int) -> List[Dict[str, Any]]:
        return self._fetchall("""
            SELECT prerequisite_course_id
            FROM course_prerequisites
            WHERE course_id = ?;
        """, (course_id,))

    def get_student_plan(self, student_id: int, semester: str) -> List[Dict[str, Any]]:
        return self._fetchall("""
            SELECT tp.course_id as course_id, c.name as name, tp.status as status
            FROM trajectory_plan tp
            JOIN courses c ON c.id = tp.course_id
            WHERE tp.student_id = ? AND tp.semester = ?
            ORDER BY c.name;
        """, (student_id, semester))

    def add_to_plan(self, student_id: int, course_id: int, semester: str) -> int:
        return self._execute("""
            INSERT OR IGNORE INTO trajectory_plan(student_id, course_id, semester, status)
            VALUES (?, ?, ?, 'planned');
        """, (student_id, course_id, semester))

    def remove_from_plan(self, student_id: int, course_id: int, semester: str) -> None:
        self._execute("""
            DELETE FROM trajectory_plan
            WHERE student_id = ? AND course_id = ? AND semester = ?;
        """, (student_id, course_id, semester))

def fix_empty_course_names(self) -> None:
    # якщо у student_courses є пусті/NULL назви — заповнюємо з каталогу
    self._execute("""
        UPDATE student_courses
        SET course_name = (SELECT name FROM courses WHERE courses.id = student_courses.course_id)
        WHERE (course_name IS NULL OR TRIM(course_name) = '')
          AND course_id IS NOT NULL;
    """)

def ensure_catalog_ready(self) -> None:
    # seed courses if empty
    existing = self._fetchall("SELECT name FROM courses LIMIT 1;")
    if not existing:
        self._executemany(
            "INSERT INTO courses(name, difficulty) VALUES (?, ?);",
            [(name, 2.0) for name in DEFAULT_COURSES],
        )

    # sync course_id in student_courses
    self._execute("""
        UPDATE student_courses
        SET course_id = (SELECT id FROM courses WHERE courses.name = student_courses.course_name)
        WHERE (course_id IS NULL OR course_id = 0)
          AND course_name IN (SELECT name FROM courses);
    """)
