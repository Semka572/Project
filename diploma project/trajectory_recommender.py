# trajectory_recommender.py
PASS_GRADE = 60.0

def recommend_courses(student, courses_taken, all_courses, prerequisites_map, p_adjusted=None):
    taken_ids = {x["course_id"] for x in courses_taken if x.get("course_id") is not None}
    passed_ids = {
        x["course_id"]
        for x in courses_taken
        if x.get("course_id") is not None and x.get("grade") is not None and float(x["grade"]) >= PASS_GRADE
    }

    def prereqs_satisfied(course_id: int) -> bool:
        reqs = prerequisites_map.get(course_id, set())
        return reqs.issubset(passed_ids)

    risk_level = "low"
    if p_adjusted is not None:
        if p_adjusted < 0.5:
            risk_level = "high"
        elif p_adjusted < 0.7:
            risk_level = "medium"

    optimal = []
    cautious = []
    must_fix = []

    # must_fix: failed courses
    for x in courses_taken:
        if x.get("course_id") is None or x.get("grade") is None:
            continue
        if float(x["grade"]) < PASS_GRADE:
            must_fix.append((int(x["course_id"]), "Рекомендовано повторити/підсилити (оцінка нижче порогу)"))

    for c in all_courses:
        cid = int(c["id"])
        if cid in taken_ids:
            continue

        if not prereqs_satisfied(cid):
            cautious.append((c, "Не виконані пререквізити"))
            continue

        difficulty = float(c.get("difficulty", 2.0))

        if risk_level == "high":
            if difficulty <= 2.0:
                optimal.append((c, "Низьке навантаження при високому ризику"))
            else:
                cautious.append((c, "Високе навантаження при високому ризику"))
        elif risk_level == "medium":
            if difficulty <= 3.0:
                optimal.append((c, "Збалансований курс при середньому ризику"))
            else:
                cautious.append((c, "Потенційно складний курс"))
        else:
            optimal.append((c, "Курс доступний, пререквізити виконані"))

    return {"risk_level": risk_level, "must_fix": must_fix, "optimal": optimal, "cautious": cautious}
