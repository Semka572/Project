# ------------------------------------------------------------
# app.py — main Flask application (Clean + Trajectory + Planner) — FINAL
# ------------------------------------------------------------
from __future__ import annotations

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
from ui_templates import (
    LOGIN_PAGE,
    REGISTER_PAGE,
    STUDENTS_PAGE,
    EDIT_PAGE,
    PREDICTION_PAGE,
)

from prediction_engine import predict
from stats_manager import compute_stats, save_stats
from history_manager import history
from course_manager import course_manager

# NEW: "2 variants what to do" (attendance + low grades) — no DB needed
from interventions import build_interventions

# NEW: variant-1 (two plans: base vs recommended) + apply
from trajectory_planner import build_two_plans


app = Flask(__name__)
app.secret_key = "super_secret_key_123"

db = Database()


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def logged_in() -> bool:
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
        username = request.form.get("username", "")
        password = request.form.get("password", "")

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
        username = request.form.get("username", "")
        password = request.form.get("password", "")

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
    if not logged_in():
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
        main_keys = ["Gcurrent", "Gmin", "Gmax", "Ls", "Ph", "actual", "Ar"]

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
            row_id = c["id"]
            enabled_flag = 1 if request.form.get(f"course_{row_id}_enabled") else 0
            grade_raw = request.form.get(f"course_{row_id}_grade")
            grade_val = float(grade_raw) if grade_raw not in ("", None) else None
            course_manager.update_course(row_id, enabled_flag, grade_val)

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
    if not logged_in():
        return redirect("/login")

    db.delete_student(sid)
    return redirect("/students")


# ------------------------------------------------------------
# PREDICT
# ------------------------------------------------------------
@app.route("/predict/<int:sid>")
def do_predict(sid: int):
    if not logged_in():
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
# TRAJECTORY (templates/) — TWO PLANS + ACTIONS
# ------------------------------------------------------------
@app.route("/trajectory/<int:student_id>")
def trajectory(student_id: int):
    if not logged_in():
        return redirect("/login")

    semester = request.args.get("semester", "2025-2")

    student = db.get_student(student_id)
    if not student:
        return "Student not found", 404

    # ensure catalog + student rows
    db.ensure_catalog_ready()
    course_manager.create_default_courses(student_id)

    courses_taken = course_manager.get_student_courses(student_id)

    # prediction
    p_initial, p_adjusted, weights = predict(student, courses_taken)

    # 2 variants: base plan vs recommended plan
    base_ids, base_reason, rec_ids, rec_reason, risk = build_two_plans(courses_taken, p_adjusted)

    # catalog lookup for display names
    all_courses = db.get_all_courses()
    name_by_id = {int(c["id"]): c["name"] for c in all_courses}

    base_plan = [{"id": cid, "name": name_by_id.get(cid, f"Course #{cid}")} for cid in base_ids]
    rec_plan = [{"id": cid, "name": name_by_id.get(cid, f"Course #{cid}")} for cid in rec_ids]

    # 2 variants "what to do next" (attendance + low grades)
    actions = build_interventions(student, courses_taken)

    # current saved plan (if any)
    plan = db.get_student_plan(student_id, semester)

    return render_template(
        "trajectory.html",
        student=student,
        semester=semester,
        p_adjusted=p_adjusted,
        risk=risk,
        plan=plan,
        # plans
        base_plan=base_plan,
        rec_plan=rec_plan,
        base_reason=base_reason,
        rec_reason=rec_reason,
        # actions (recommended/caution)
        actions=actions,
    )


# ------------------------------------------------------------
# APPLY PLAN (this is the "control action" — Управління траєкторією)
# ------------------------------------------------------------
@app.route("/trajectory/<int:student_id>/apply", methods=["POST"])
def trajectory_apply(student_id: int):
    if not logged_in():
        return redirect("/login")

    semester = request.form.get("semester", "2025-2")
    variant = request.form.get("variant", "base")  # "base" or "rec"

    student = db.get_student(student_id)
    if not student:
        return "Student not found", 404

    db.ensure_catalog_ready()
    course_manager.create_default_courses(student_id)

    courses_taken = course_manager.get_student_courses(student_id)
    p_initial, p_adjusted, weights = predict(student, courses_taken)

    base_ids, base_reason, rec_ids, rec_reason, risk = build_two_plans(courses_taken, p_adjusted)

    chosen_ids = base_ids if variant == "base" else rec_ids

    # Requires these methods in Database:
    # - clear_plan(student_id, semester)
    # - bulk_add_to_plan(student_id, semester, course_ids)
    db.clear_plan(student_id, semester)
    db.bulk_add_to_plan(student_id, semester, chosen_ids)

    return redirect(url_for("trajectory", student_id=student_id, semester=semester))


# ------------------------------------------------------------
# (Optional) manual plan tweaks if you keep these endpoints
# ------------------------------------------------------------
@app.route("/trajectory/<int:student_id>/add", methods=["POST"])
def trajectory_add(student_id: int):
    if not logged_in():
        return redirect("/login")

    semester = request.form.get("semester", "2025-2")
    course_id = int(request.form["course_id"])
    db.add_to_plan(student_id, course_id, semester)
    return redirect(url_for("trajectory", student_id=student_id, semester=semester))


@app.route("/trajectory/<int:student_id>/remove", methods=["POST"])
def trajectory_remove(student_id: int):
    if not logged_in():
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
