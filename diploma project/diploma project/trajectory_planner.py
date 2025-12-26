# trajectory_planner.py
PASS_GRADE = 60.0

def _risk_level(p_adjusted: float | None) -> str:
    if p_adjusted is None:
        return "medium"
    if p_adjusted < 0.5:
        return "high"
    if p_adjusted < 0.7:
        return "medium"
    return "low"


def build_two_plans(student_courses: list[dict], p_adjusted: float | None):
    """
    student_courses: список з course_manager.get_student_courses(student_id)
      очікуємо: course_id, name/course_name, enabled, grade, difficulty
    Повертає:
      base_ids, base_reason
      rec_ids, rec_reason
    """

    risk = _risk_level(p_adjusted)

    # курси з валідним course_id
    rows = [c for c in student_courses if c.get("course_id") is not None]

    # completed / failed
    completed = {int(c["course_id"]) for c in rows if c.get("grade") is not None and float(c["grade"]) >= PASS_GRADE}
    failed = [c for c in rows if c.get("grade") is not None and float(c["grade"]) < PASS_GRADE]

    # кандидати = не completed
    candidates = [c for c in rows if int(c["course_id"]) not in completed]

    # -------------------------
    # Варіант A: "поточний план"
    # -------------------------
    enabled = [c for c in candidates if int(c.get("enabled", 0)) == 1]
    if enabled:
        base = enabled
        base_reason = "Поточний план сформовано з обраних (enabled) дисциплін."
    else:
        # якщо користувач не відмітив enabled — беремо перші 4 найлегші як дефолт
        base = sorted(candidates, key=lambda x: float(x.get("difficulty", 2.0)))[:4]
        base_reason = "Enabled не вибрані — сформовано базовий план (4 дисципліни) з найнижчим навантаженням."

    base_ids = [int(c["course_id"]) for c in base]

    # -------------------------
    # Варіант B: "рекомендований план" (залежить від ризику)
    # -------------------------
    rec = []

    # 1) якщо є провалені — в рекомендований додаємо їх першими (перездача/повтор)
    for f in failed:
        rec.append(f)

    # 2) далі добираємо за ризиком
    if risk == "high":
        limit = 2   # мінімальне навантаження
        pool = sorted(candidates, key=lambda x: float(x.get("difficulty", 2.0)))
        rec_reason = "Високий ризик: рекомендовано мінімальне навантаження + фокус на проблемних дисциплінах."
    elif risk == "medium":
        limit = 4
        pool = sorted(candidates, key=lambda x: float(x.get("difficulty", 2.0)))
        rec_reason = "Середній ризик: рекомендовано помірне навантаження та поступове закриття базових дисциплін."
    else:
        limit = 5
        pool = sorted(candidates, key=lambda x: (-float(x.get("difficulty", 2.0)), x["name"]))
        rec_reason = "Низький ризик: рекомендовано інтенсивніша траєкторія (можна брати складніші дисципліни)."

    # додаємо з pool, уникаючи дублю
    used_ids = {int(c["course_id"]) for c in rec if c.get("course_id") is not None}
    for c in pool:
        cid = int(c["course_id"])
        if cid in used_ids:
            continue
        rec.append(c)
        used_ids.add(cid)
        if len(used_ids) >= limit:
            break

    rec_ids = list(used_ids)

    return (base_ids, base_reason, rec_ids, rec_reason, risk)
