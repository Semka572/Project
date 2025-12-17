# ------------------------------------------------------------
# app.py — main Flask application (Clean Version)
# ------------------------------------------------------------
from flask import Flask, request, redirect, session, render_template_string
import os

from database import Database
from ui_templates import LOGIN_PAGE, REGISTER_PAGE, STUDENTS_PAGE, EDIT_PAGE, PREDICTION_PAGE
from prediction_engine import predict
from stats_manager import compute_stats, save_stats
from history_manager import history
from course_manager import course_manager      # <-- IMPORTANT

app = Flask(__name__)
app.secret_key = "super_secret_key_123"

db = Database()


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def logged_in():
    return "user_id" in session


# ------------------------------------------------------------
# HOME
# ------------------------------------------------------------
@app.route("/")
def home():
    if not logged_in():
        return redirect("/login")
    return redirect("/students")


# ------------------------------------------------------------
# LOGIN
# ------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        user = db.get_user(username)

        if user and user["password"] == password:
            session["user_id"] = user["id"]
            return redirect("/students")

        return render_template_string(
            LOGIN_PAGE + "<p style='color:red'>Invalid login</p>"
        )

    return render_template_string(LOGIN_PAGE)


# ------------------------------------------------------------
# REGISTER
# ------------------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        if db.get_user(username):
            return render_template_string(
                REGISTER_PAGE + "<p style='color:red'>User already exists</p>"
            )

        db.add_user(username, password)
        return redirect("/login")

    return render_template_string(REGISTER_PAGE)


# ------------------------------------------------------------
# LOGOUT
# ------------------------------------------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ------------------------------------------------------------
# STUDENT LIST
# ------------------------------------------------------------
@app.route("/students")
def students():

    if not logged_in():
        return redirect("/login")

    all_students = db.list_students(session["user_id"])
    return render_template_string(STUDENTS_PAGE, students=all_students)


# ------------------------------------------------------------
# ADD STUDENT
# ------------------------------------------------------------
@app.route("/add_student", methods=["POST"])
def add_student():

    if not logged_in():
        return redirect("/login")

    name = request.form.get("name", "Student")

    # Create student and get ID
    sid = db.add_student(session["user_id"], name)

    # Create default courses for new student
    course_manager.create_default_courses(sid)

    return redirect("/students")


# ------------------------------------------------------------
# EDIT STUDENT
# ------------------------------------------------------------
@app.route("/edit/<int:sid>", methods=["GET", "POST"])
def edit(sid):

    if not logged_in():
        return redirect("/login")

    student = db.get_student(sid)
    if not student:
        return "Student not found", 404

    # Load all courses (from course_manager)
    courses = course_manager.get_student_courses(sid)

    if request.method == "POST":

        # ---------------- Update student fields ----------------
        fields = {}
        main_keys = ["Gcurrent", "Gmin", "Gmax", "Ls", "Ph", "actual"]

        for key in main_keys:
            val = request.form.get(key)
            if val not in ("", None):
                try:
                    fields[key] = float(val)
                except:
                    pass

        if fields:
            db.update_student(sid, **fields)

        # ---------------- Update courses ----------------
        for c in courses:
            cid = c["id"]

            enabled_flag = 1 if request.form.get(f"course_{cid}_enabled") else 0
            grade_raw = request.form.get(f"course_{cid}_grade")
            grade_val = float(grade_raw) if grade_raw not in ("", None) else None

            course_manager.update_course(cid, enabled_flag, grade_val)

        return redirect("/students")

    return render_template_string(
        EDIT_PAGE,
        student=student,
        courses=courses
    )


# ------------------------------------------------------------
# DELETE STUDENT
# ------------------------------------------------------------
@app.route("/delete/<int:sid>")
def delete(sid):

    if not logged_in():
        return redirect("/login")

    db.delete_student(sid)
    #course_manager.delete_courses_for_student(sid)

    return redirect("/students")


# ------------------------------------------------------------
# PREDICT
# ------------------------------------------------------------
@app.route("/predict/<int:sid>")
def do_predict(sid):

    if not logged_in():
        return redirect("/login")

    student = db.get_student(sid)
    if not student:
        return "Student not found", 404

    courses = course_manager.get_student_courses(sid)

    # Update internal global statistics (optional)
    stats = compute_stats()
    save_stats(stats)

    # MAIN PREDICTION ENGINE
    p_initial, p_adjusted, weights = predict(student, courses)

    # Save history
    history.add_record(
        student_id=sid,
        p_initial=p_initial,
        p_adjusted=p_adjusted,
        weights=weights,
        actual=student["actual"]
    )

    return render_template_string(
        PREDICTION_PAGE,
        student=student,
        p_initial=p_initial,
        p_adjusted=p_adjusted,
        weights=weights
    )


# ------------------------------------------------------------
# RUN SERVER
# ------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
