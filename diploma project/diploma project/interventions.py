# interventions.py
from __future__ import annotations
from typing import Dict, List, Any, Optional

PASS_GRADE = 60.0
ATTENDANCE_LOW = 0.60

# Демонстраційні "пари/теми" (можеш змінювати як хочеш)
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

# Демонстраційні "події" (дедлайни/колоквіуми) — без БД
# Можна вказувати як текст без дат, або з датою рядком.
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
    """
    Повертає 2 списки:
      - recommended: що зробити (поради/дії)
      - caution: попередження (дедлайни/колоквіуми)
    student_courses: з course_manager.get_student_courses(student_id)
      очікуємо: name/course_name, enabled, grade
    """
    recommended: List[str] = []
    caution: List[str] = []

    # -------------------------
    # 1) Низька відвідуваність (Ar)
    # -------------------------
    ar = student.get("Ar")
    if ar is not None and float(ar) < ATTENDANCE_LOW:
        # фокус — на 1-2 курсах: спочатку enabled, якщо нема — просто перші
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

    # -------------------------
    # 2) Низькі оцінки по конкретних курсах
    # -------------------------
    for c in student_courses:
        g = c.get("grade")
        if g is None:
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

            # попередження про події (дедлайни/колоквіуми)
            events = COURSE_EVENTS.get(cname, [])
            for e in events[:2]:  # максимум 2, щоб не захламлювати
                if e["type"] == "deadline":
                    caution.append(f"Обережно: {e['text']}.")
                elif e["type"] == "colloquium":
                    caution.append(f"Обережно: {e['text']}.")
                else:
                    caution.append(f"Обережно: {e['text']}.")

    # якщо взагалі нема повідомлень — додамо нейтральне
    if not recommended:
        recommended.append("Рекомендація: продовжувати навчання за планом та підтримувати регулярну активність.")
    if not caution:
        caution.append("Немає критичних попереджень за поточними даними.")

    return {"recommended": recommended, "caution": caution}
