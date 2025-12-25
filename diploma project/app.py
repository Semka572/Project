# ------------------------------------------------------------
# app.py — main Flask application (Clean + Trajectory) — FIXED
# ------------------------------------------------------------
from flask import (
    Flask,
    request,
    redirect,
    session,
    render_template_string,
    render_template,
    url_for,
)

from database import Database
from ui_templates import LOGIN_PAGE, REGISTER_PAGE, STUDENTS_PAGE, EDIT_PAGE, PREDICTION_PAGE

from prediction_engine import predict
from stats_manager import compute_stats, save_stats
from history_manager import history
from course_manager import course_manager
from trajectory_recommender import recommend_courses


app = Flask(__name__)
app.secret_key = "super_secret_key_123"

db = Database()


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def logged_in() -> bool:
    return "user_id" in session


def login_required() -> bool:
    return logged_in()


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

        return render_template_string(LOGIN_PAGE + "<p style='color:red'>Invalid login</p>")

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
            return render_template_string(REGISTER_PAGE + "<p style='color:red'>User already exists</p>")

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
    if not login_required():
        return redirect("/login")

    all_students = db.list_students(session["user_id"])
    return render_template_string(STUDENTS_PAGE, students=all_students)


# ------------------------------------------------------------
# ADD STUDENT
# ------------------------------------------------------------
@app.route("/add_student", methods=["POST"])
def add_student():
    if not login_required():
        return redirect("/login")

    name = request.form.get("name", "Student")

    # Create student and get ID
    sid = db.add_student(session["user_id"], name)

    # IMPORTANT: ensure catalog + create student course rows with NAMES
    db.ensure_catalog_ready()
    course_manager.create_default_courses(sid)

    return redirect("/students")


# ------------------------------------------------------------
# EDIT STUDENT
# ------------------------------------------------------------
@app.route("/edit/<int:sid>", methods=["GET", "POST"])
def edit(sid: int):
    if not login_required():
        return redirect("/login")

    student = db.get_student(sid)
    if not student:
        return "Student not found", 404

    # IMPORTANT: guarantee student has courses with names for UI
    db.ensure_catalog_ready()
    course_manager.create_default_courses(sid)
    courses = course_manager.get_student_courses(sid)

    if request.method == "POST":
        # -------- Update student numeric fields --------
        fields = {}
        main_keys = ["Gcurrent", "Gmin", "Gmax", "Ls", "Ph", "actual"]

        for key in main_keys:
            val = request.form.get(key)
            if val not in ("", None):
                try:
                    fields[key] = float(val)
                except ValueError:
                    pass

        if fields:
            db.update_student(sid, **fields)

        # -------- Update courses (enabled + grade) --------
        for c in courses:
            cid = c["id"]
            enabled_flag = 1 if request.form.get(f"course_{cid}_enabled") else 0
            grade_raw = request.form.get(f"course_{cid}_grade")
            grade_val = float(grade_raw) if grade_raw not in ("", None) else None
            course_manager.update_course(cid, enabled_flag, grade_val)

        # keep data consistent
        db.ensure_catalog_ready()
        course_manager.create_default_courses(sid)

        return redirect("/students")

    return render_template_string(EDIT_PAGE, student=student, courses=courses)


# ------------------------------------------------------------
# DELETE STUDENT
# ------------------------------------------------------------
@app.route("/delete/<int:sid>")
def delete(sid: int):
    if not login_required():
        return redirect("/login")

    db.delete_student(sid)
    return redirect("/students")


# ------------------------------------------------------------
# PREDICT
# ------------------------------------------------------------
@app.route("/predict/<int:sid>")
def do_predict(sid: int):
    if not login_required():
        return redirect("/login")

    student = db.get_student(sid)
    if not student:
        return "Student not found", 404

    db.ensure_catalog_ready()
    course_manager.create_default_courses(sid)

    courses = course_manager.get_student_courses(sid)

    # optional stats
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
        actual=student.get("actual"),
    )

    # Render old prediction page (string template) + add trajectory button
    html = render_template_string(
        PREDICTION_PAGE,
        student=student,
        p_initial=p_initial,
        p_adjusted=p_adjusted,
        weights=weights,
    )

    html += f"""
    <hr>
    <div style="margin-top: 10px;">
      <a href="{url_for('trajectory', student_id=sid, semester='2025-2')}">
        <button type="button">Перейти до траєкторії</button>
      </a>
    </div>
    """

    return html


# ------------------------------------------------------------
# TRAJECTORY (NEW UI via templates/)
# ------------------------------------------------------------
@app.route("/trajectory/<int:student_id>")
def trajectory(student_id: int):
    if not login_required():
        return redirect("/login")

    semester = request.args.get("semester", "2025-2")

    student = db.get_student(student_id)
    if not student:
        return "Student not found", 404

    # IMPORTANT: ensure catalog exists + student has named course rows
    db.ensure_catalog_ready()
    course_manager.create_default_courses(student_id)

    # Take student courses from course_manager (it repairs names & ids)
    courses_taken = course_manager.get_student_courses(student_id)

    # Catalog for recommendations
    all_courses = db.get_all_courses()

    # prediction for risk level
    p_initial, p_adjusted, weights = predict(student, courses_taken)

    # prerequisites map: course_id -> set(prereq_ids)
    prerequisites_map = {}
    for c in all_courses:
        cid = int(c["id"])
        reqs = db.get_prerequisites(cid)
        prerequisites_map[cid] = {int(r["prerequisite_course_id"]) for r in reqs}

    # Normalize taken courses for recommender:
    # Use catalog course_id, not student_courses row id
    taken_norm = []
    for x in courses_taken:
        cid = x.get("course_id")
        if cid is None:
            continue
        taken_norm.append({"course_id": int(cid), "grade": x.get("grade")})

    rec = recommend_courses(
        student=student,
        courses_taken=taken_norm,
        all_courses=all_courses,
        prerequisites_map=prerequisites_map,
        p_adjusted=p_adjusted,
    )

    plan = db.get_student_plan(student_id, semester)

    return render_template(
        "trajectory.html",
        student=student,
        semester=semester,
        p_adjusted=p_adjusted,
        rec=rec,
        plan=plan,
    )


@app.route("/trajectory/<int:student_id>/add", methods=["POST"])
def trajectory_add(student_id: int):
    if not login_required():
        return redirect("/login")

    semester = request.form.get("semester", "2025-2")
    course_id = int(request.form["course_id"])
    db.add_to_plan(student_id, course_id, semester)
    return redirect(url_for("trajectory", student_id=student_id, semester=semester))


@app.route("/trajectory/<int:student_id>/remove", methods=["POST"])
def trajectory_remove(student_id: int):
    if not login_required():
        return redirect("/login")

    semester = request.form.get("semester", "2025-2")
    course_id = int(request.form["course_id"])
    db.remove_from_plan(student_id, course_id, semester)
    return redirect(url_for("trajectory", student_id=student_id, semester=semester))


# ------------------------------------------------------------
# RUN SERVER
# ------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
