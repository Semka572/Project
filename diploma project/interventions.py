from __future__ import annotations
from typing import Dict, List, Any

PASS_GRADE = 60.0
ATTENDANCE_LOW = 0.60

LECTURE_TOPICS: Dict[str, List[Dict[str, Any]]] = {
    "Mathematics": [
        {"lecture": 2, "topic": "Systems of linear equations"},
        {"lecture": 3, "topic": "Matrices and operations"},
    ],
    "Programming": [
        {"lecture": 5, "topic": "Functions and recursion"},
        {"lecture": 6, "topic": "OOP basics"},
    ],
    "Databases": [
        {"lecture": 3, "topic": "SQL SELECT/JOIN практика"},
        {"lecture": 4, "topic": "Normalization"},
    ],
}


COURSE_EVENTS: Dict[str, List[Dict[str, str]]] = {
    "Programming": [
        {"type": "deadline", "text": "Дедлайн: Lab 2 (структури даних) — до кінця тижня"},
        {"type": "colloquium", "text": "Колоквіум: базові алгоритми — наступний тиждень"},
    ],
    "Databases": [
        {"type": "deadline", "text": "Дедлайн: ER-модель + SQL-запити — до п’ятниці"},
        {"type": "colloquium", "text": "Колоквіум: JOIN/агрегації — наступна пара"},
    ],
    "Mathematics": [
        {"type": "deadline", "text": "Дедлайн: домашня №1 (матриці) — до понеділка"},
    ],
}


def build_interventions(student: dict, student_courses: List[dict]) -> Dict[str, List[str]]:
    recommended: List[str] = []
    caution: List[str] = []

    ar = student.get("Ar")
    ar_val = None
    if ar is not None and ar != "":
        try:
            ar_val = float(ar)
        except Exception:
            ar_val = None

    if ar_val is not None:
        if ar_val > 1.5:
            ar_val = ar_val / 100.0

        if ar_val < ATTENDANCE_LOW:
            enabled = [c for c in student_courses if int(c.get("enabled", 0)) == 1]
            focus = enabled[:2] if enabled else student_courses[:2]

            for c in focus:
                cname = c.get("name") or c.get("course_name") or "Курс"
                topics = LECTURE_TOPICS.get(cname)
                if topics:
                    t = topics[0]
                    recommended.append(
                        f"Низька відвідуваність: відвідати пару №{t['lecture']} з {cname} (буде розбір теми: {t['topic']})."
                    )
                else:
                    recommended.append(
                        f"Низька відвідуваність: рекомендовано відвідати найближчу пару з {cname} (ключова тема)."
                    )

    for c in student_courses:
        g = c.get("grade")
        if g is None or g == "":
            continue

        try:
            grade_val = float(g)
        except Exception:
            continue

        cname = c.get("name") or c.get("course_name") or "Курс"

        if grade_val < PASS_GRADE:
            recommended.append(
                f"Низька оцінка з {cname}: рекомендовано повторити матеріал і виконати додаткові вправи."
            )

            events = COURSE_EVENTS.get(cname, [])
            for e in events[:2]:
                caution.append(f"Обережно: {e['text']}.")

    if not recommended:
        recommended.append("Рекомендація: продовжувати навчання за планом та підтримувати регулярну активність.")
    if not caution:
        caution.append("Немає критичних попереджень за поточними даними.")

    return {"recommended": recommended, "caution": caution}
