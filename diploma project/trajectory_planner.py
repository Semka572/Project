PASS_GRADE = 60.0

DEFAULT_ORDER = [
    "Algorithms",
    "Computer Architecture",
    "Databases",
    "Discrete Structures",
    "Linear Algebra",
    "Mathematics",
    "Probability and Statistics",
    "Programming",
]


def _risk_level(p_adjusted: float | None) -> str:
    if p_adjusted is None:
        return "Середній"
    p_score = p_adjusted * 100.0 if p_adjusted <= 1.0 else p_adjusted
    if p_score < 60.0:
        return "Високий"
    if p_score < 70.0:
        return "Середній"
    return "Низький"


def _name(x: dict) -> str:
    return str(x.get("name") or x.get("course_name") or "").strip()


def _grade_val(x: dict) -> float:
    g = x.get("grade")
    if g is None or g == "":
        return 101.0
    try:
        return float(g)
    except Exception:
        return 101.0


def _order_index(x: dict) -> int:
    n = _name(x)
    try:
        return DEFAULT_ORDER.index(n)
    except ValueError:
        return 10**9


def build_two_plans(student_courses: list[dict], p_adjusted: float | None):
    risk = _risk_level(p_adjusted)

    rows = [c for c in student_courses if c.get("course_id") is not None]
    rows = [c for c in rows if int(c.get("enabled", 0)) == 1]

    completed = {
        int(c["course_id"])
        for c in rows
        if c.get("grade") is not None and float(c["grade"]) >= PASS_GRADE
    }

    failed = [
        c
        for c in rows
        if c.get("grade") is not None and float(c["grade"]) < PASS_GRADE
    ]

    candidates = [c for c in rows if int(c["course_id"]) not in completed]

    p_score = None
    if p_adjusted is not None:
        p_score = p_adjusted * 100.0 if p_adjusted <= 1.0 else p_adjusted

    enabled_completed = bool(rows) and all(int(c["course_id"]) in completed for c in rows)

    if p_score is not None and p_score < 60.0 and enabled_completed:
        rec_reason = "Низький прогноз: рекомендовано зосередитися на підвищенні балів з основних предметів та стабілізувати результати."
    else:
        if risk == "Високий":
            rec_reason = "Високий ризик: рекомендовано мінімальне навантаження та фокус на проблемних дисциплінах."
        elif risk == "Середній":
            rec_reason = "Середній ризик: рекомендовано помірне навантаження та поступове закриття базових дисциплін."
        else:
            rec_reason = "Низький ризик: рекомендовано інтенсивніша траєкторія, можливе додавання курсів."

    limit = 2 if risk == "Високий" else (4 if risk == "Середній" else 5)

    base_source = failed if failed else candidates
    base_sorted = sorted(base_source, key=_order_index)
    base = base_sorted[:limit] if limit > 0 else []
    if failed:
        base_reason = "Поточний план сформовано з проблемних дисциплін у порядку навчального списку."
    else:
        base_reason = "Поточний план сформовано з увімкнених дисциплін у порядку навчального списку."
    base_ids = [int(c["course_id"]) for c in base]

    pool_sorted = sorted(
        candidates,
        key=lambda x: (_grade_val(x), _order_index(x))
    )

    used_ids = set()
    rec = []

    for c in pool_sorted:
        cid = int(c["course_id"])
        if cid in used_ids:
            continue
        rec.append(c)
        used_ids.add(cid)
        if len(used_ids) >= limit:
            break

    rec_ids = [int(c["course_id"]) for c in rec]

    return (base_ids, base_reason, rec_ids, rec_reason, risk)
