"""
MedExplain AI -- app.py
========================
Main Streamlit entry point.

This file is intentionally kept to page routing / composition. All medical
knowledge lives in data/*.json, all classification logic lives in
src/classifier.py, all explanation/question text selection lives in
src/explainer.py and src/questions.py, and all styling/rendering helpers
live in src/ui_components.py.

Run locally with:
    streamlit run app.py
"""

from __future__ import annotations

from typing import Optional

import streamlit as st

from src import ui_components as ui
from src.classifier import ValidationError, classify_patient_results, validate_value
from src.data_loader import DataLoadError, load_lab_tests, load_lab_tests_meta, load_scenarios
from src.explainer import build_explanations
from src.models import LabResult, PatientScenario
from src.questions import select_questions_by_test
from src.summary import build_summary

PAGES = [
    "עמוד הבית",
    "לוח מטופל",
    "כיצד זה עובד",
    "למה לא ChatGPT?",
    "בטיחות ואתיקה",
    "משוב מהמטופל",
    "ארכיטקטורת המערכת",
]

TREND_TEST_KEYS = ["hba1c", "ldl", "hemoglobin", "wbc", "ferritin"]

TEST_ORDER = ["wbc", "hemoglobin", "ferritin", "hba1c", "ldl", "hdl", "triglycerides", "crp"]


# ---------------------------------------------------------------------------
# Cached data loading
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def get_lab_tests() -> dict:
    return load_lab_tests()


@st.cache_data(show_spinner=False)
def get_lab_tests_meta() -> dict:
    return load_lab_tests_meta()


@st.cache_data(show_spinner=False)
def get_scenarios() -> list[PatientScenario]:
    return load_scenarios()


# ---------------------------------------------------------------------------
# Shared rendering: takes classified results through to full dashboard output
# ---------------------------------------------------------------------------

def render_full_analysis(
    lab_results: list[LabResult],
    sex: Optional[str],
    age: Optional[int],
    notes: Optional[str],
    lab_tests: dict,
) -> None:
    if not lab_results:
        st.info("לא הוזנו תוצאות בדיקה לניתוח. יש להזין לפחות ערך אחד.")
        return

    classified = classify_patient_results(lab_results, lab_tests, sex=sex, age=age)

    st.markdown("#### תוצאות הבדיקה")
    ui.render_results_table(classified)

    summary = build_summary(classified)
    st.markdown("#### סיכום")
    ui.render_summary_card(summary)

    explanations = build_explanations(classified, lab_tests)
    if explanations:
        questions_by_test = select_questions_by_test(classified, lab_tests, notes=notes)
        st.markdown("#### הסברים והמלצות לשיחה עם הרופא/ה")
        for explanation in explanations:
            questions = questions_by_test.get(explanation["test_key"], [])
            ui.render_explanation_card(explanation, questions)
    else:
        st.success("לא נמצאו ממצאים גבוליים או חריגים הדורשים הסבר נוסף.")

    st.caption(
        "המידע המוצג הוא הסבר כללי בלבד ואינו מהווה אבחנה או המלצה רפואית אישית. "
        "לכל שאלה לגבי המשמעות הקלינית של התוצאות יש לפנות לרופא/ת המשפחה."
    )


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

def render_home_page() -> None:
    ui.render_app_header("MedExplain AI", "הבנה שקטה של תוצאות בדיקות דם, לפני השיחה עם הרופא/ה")

    st.markdown(
        """
        <div class="me-card">
        <p>
        מטופלים רבים מקבלים כיום תוצאות בדיקות דם דיגיטליות עוד לפני שיחה עם הרופא/ה המטפל/ת.
        לעיתים מופיע ערך המסומן כחריג, מבלי שברור מה בדיוק הבדיקה מודדת, האם מדובר בסטייה
        מהותית או קלה, והאם יש לכך הקשר עם תוצאות נוספות.
        </p>
        <p>
        המצב הזה עלול להוביל לחיפושים לא מבוקרים ברשת, להעתקת מידע רפואי אישי אל כלי AI
        כלליים וציבוריים, ולשיחה לא ממוקדת עם הרופא/ה. <b>MedExplain AI</b> הוא אב-טיפוס
        לימודי שמטרתו לגשר בין קבלת התוצאה להבנתה, ולסייע למטופל להגיע לשיחה עם הרופא/ה
        מוכן/ה יותר עם השאלות הנכונות.
        </p>
        <p><b>המערכת נועדה לתמוך בתקשורת בין המטופל לרופא/ה, ולא להחליף אותה.</b></p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    ui.render_disclaimer(
        "זהו פרויקט גמר אקדמי להדגמה בלבד (Proof of Concept). המערכת אינה מכשיר רפואי, "
        "אינה מספקת אבחנה או ייעוץ רפואי, ומבוססת כולה על נתונים סינתטיים. "
        "טווחי הייחוס המוצגים הם ערכים לדוגמה ואינם תחליף לטווח הייחוס של המעבדה או לפרשנות רפואית."
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            '<div class="me-card"><h4>🧬 נתונים רפואיים מובנים</h4>'
            "<p>כל הידע הרפואי מוגדר בקובצי JSON נפרדים מקוד האפליקציה, "
            "כך שניתן לעדכן טווחי ייחוס והסברים ללא שינוי בלוגיקה.</p></div>",
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            '<div class="me-card"><h4>⚙️ סיווג דטרמיניסטי</h4>'
            "<p>הסיווג לתקין / גבולי / חריג מתבצע על-ידי כללים מספריים מפורשים, "
            "ולא על-ידי מודל שפה בזמן אמת.</p></div>",
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            '<div class="me-card"><h4>🩺 שאלות לרופא/ה</h4>'
            "<p>לכל ממצא נבחרות שאלות ממוקדות ורלוונטיות, שיעזרו למטופל להגיע "
            "מוכן/ה יותר לשיחה הקלינית.</p></div>",
            unsafe_allow_html=True,
        )

    st.markdown("")
    if st.button("מעבר ללוח המטופל ⟵", type="primary"):
        st.session_state["page"] = "לוח מטופל"
        st.rerun()


def render_dashboard_page(lab_tests: dict, scenarios: list[PatientScenario]) -> None:
    ui.render_app_header("לוח מטופל", "בחרו תרחיש הדגמה סינתטי, או הזינו ערכים באופן ידני")

    mode = st.radio(
        "אופן השימוש",
        options=["תרחיש הדגמה סינתטי", "הזנה ידנית"],
        horizontal=True,
        label_visibility="collapsed",
    )

    if mode == "תרחיש הדגמה סינתטי":
        render_scenario_mode(lab_tests, scenarios)
    else:
        render_manual_mode(lab_tests)


def render_scenario_mode(lab_tests: dict, scenarios: list[PatientScenario]) -> None:
    if not scenarios:
        st.warning("לא נמצאו תרחישי הדגמה זמינים.")
        return

    labels = [f"{s.title} — {s.patient_name}" for s in scenarios]
    choice = st.selectbox("בחירת תרחיש הדגמה (מטופל סינתטי)", options=labels)
    scenario = scenarios[labels.index(choice)]

    sex_label = "גבר" if scenario.sex == "male" else "אישה"
    st.markdown(
        f"""
        <div class="me-card">
            <h4>{scenario.patient_name}</h4>
            <p>גיל: {scenario.age} &nbsp;|&nbsp; מין: {sex_label}</p>
            <p>{scenario.context}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("מדובר בדמות ובנתונים סינתטיים לחלוטין, שנוצרו לצורך הדגמה בלבד.")

    lab_results = [
        LabResult(
            test_key=key,
            value=value,
            previous_value=scenario.previous_values.get(key),
        )
        for key, value in scenario.lab_values.items()
        if key in lab_tests
    ]

    render_full_analysis(lab_results, scenario.sex, scenario.age, scenario.notes, lab_tests)


def render_manual_mode(lab_tests: dict) -> None:
    st.markdown(
        '<div class="me-card"><p>ניתן להזין רק את הבדיקות שבוצעו בפועל — '
        "כל השדות אופציונליים, והמערכת תנתח רק את מה שהוזן.</p></div>",
        unsafe_allow_html=True,
    )

    with st.form("manual_input_form"):
        col_age, col_sex = st.columns(2)
        with col_age:
            age_raw = st.text_input("גיל (אופציונלי)", value="")
        with col_sex:
            sex_label = st.selectbox("מין (נדרש עבור בדיקות תלויות מין)", options=["לא צוין", "אישה", "גבר"])

        st.markdown("##### ערכי בדיקות")
        raw_values: dict[str, str] = {}
        raw_previous: dict[str, str] = {}

        for key in TEST_ORDER:
            test_def = lab_tests[key]
            label = f"{test_def['name_he']} ({test_def['abbreviation']}) — {test_def['unit']}"
            if key in TREND_TEST_KEYS:
                c1, c2 = st.columns([2, 1])
                with c1:
                    raw_values[key] = st.text_input(label, value="", key=f"cur_{key}")
                with c2:
                    raw_previous[key] = st.text_input(
                        "ערך קודם (אופציונלי)", value="", key=f"prev_{key}"
                    )
            else:
                raw_values[key] = st.text_input(label, value="", key=f"cur_{key}")

        notes = st.text_area("הערות קליניות רלוונטיות (אופציונלי, לדוגמה: 'מחלה ויראלית לאחרונה')", value="")
        submitted = st.form_submit_button("נתח תוצאות", type="primary")

    if not submitted:
        return

    sex_map = {"אישה": "female", "גבר": "male", "לא צוין": None}
    sex = sex_map[sex_label]

    age: Optional[int] = None
    if age_raw.strip():
        try:
            age = int(float(age_raw.strip()))
        except ValueError:
            st.error("הגיל שהוזן אינו תקין. נא להזין מספר בלבד.")
            return

    lab_results: list[LabResult] = []
    errors: list[str] = []

    for key in TEST_ORDER:
        raw = raw_values.get(key, "").strip()
        if not raw:
            continue
        try:
            value = validate_value(key, raw, lab_tests)
        except ValidationError as exc:
            errors.append(f"{lab_tests[key]['name_he']}: {exc}")
            continue

        previous_value = None
        if key in TREND_TEST_KEYS:
            raw_prev = raw_previous.get(key, "").strip()
            if raw_prev:
                try:
                    previous_value = validate_value(key, raw_prev, lab_tests)
                except ValidationError as exc:
                    errors.append(f"{lab_tests[key]['name_he']} (ערך קודם): {exc}")

        lab_results.append(LabResult(test_key=key, value=value, previous_value=previous_value))

    if errors:
        for err in errors:
            st.error(err)

    if not lab_results and not errors:
        st.warning("לא הוזן אף ערך בדיקה. נא להזין לפחות בדיקה אחת.")
        return

    if lab_results:
        render_full_analysis(lab_results, sex, age, notes, lab_tests)


def render_how_it_works_page() -> None:
    ui.render_app_header("כיצד זה עובד", "מהזנת נתונים ועד להסבר מותאם למטופל")

    st.markdown(
        """
        <div class="me-card">
        <p>
        המערכת פועלת כרצף שלבים ברור וניתן להסבר, כדי שגם מי שאינו איש/אשת תוכנה יוכל/תוכל
        להבין מה קורה מאחורי הקלעים:
        </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    steps = [
        "בחירת תרחיש הדגמה או הזנת ערכים ידנית",
        "בדיקת תקינות הקלט (ערכים חסרים, לא מספריים או בלתי אפשריים)",
        "סיווג דטרמיניסטי מול טווחי ייחוס מוגדרים (תקין / גבולי / חריג)",
        "בחירת הסבר ושאלות לרופא/ה המתאימות לממצא הספציפי",
        "בדיקת חסמי בטיחות (ניסוח לא-אבחנתי, לשון זהירה)",
        "הצגה למטופל בלוח מטופל בעברית מלאה",
    ]
    ui.render_architecture_flow(steps)

    st.markdown("#### שני מצבי שימוש")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            '<div class="me-card"><h4>🧪 תרחישי הדגמה</h4>'
            "<p>12 מטופלים סינתטיים המדגימים מצבים שונים: מערך תקין לחלוטין, ועד "
            "שילובים של כמה ממצאים גבוליים או חריגים יחד.</p></div>",
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            '<div class="me-card"><h4>✍️ הזנה ידנית</h4>'
            "<p>ניתן להזין ערכים אישיים (לדוגמה, לצורך הדגמה בכיתה). כל שדה אופציונלי, "
            "והמערכת מנתחת רק את מה שהוזן בפועל.</p></div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        <div class="me-card">
        <h4>📈 מעקב מגמות (אופציונלי)</h4>
        <p>
        עבור מספר בדיקות מרכזיות (כגון HbA1c, LDL, המוגלובין, WBC ופריטין) ניתן להזין גם
        ערך קודם. המערכת תציג האם הערך <b>עלה</b> או <b>ירד</b> לעומת הבדיקה הקודמת — ללא
        כל טענה לגבי הסיבה לשינוי. הבנה קלינית תלויה לרוב במגמה לאורך זמן, ולא רק בערך בודד.
        </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_why_not_chatgpt_page() -> None:
    ui.render_app_header("למה לא ChatGPT?", "ההבדל בין הדבקת תוצאות בכלי AI כללי לבין כלי ייעודי")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            """
            <div class="me-card">
            <h4>🌐 כלי AI כללי וציבורי</h4>
            <ul>
                <li>המטופל מעתיק ידנית מידע רפואי אישי אל כלי חיצוני</li>
                <li>אין הקשר קליני מובנה מעבר למה שהוזן בשיחה</li>
                <li>קיימת אפשרות לפלט לא עקבי בין שיחות שונות</li>
                <li>המידע יוצא מחוץ לזרימת העבודה הרפואית הרגילה</li>
                <li>אין חיבור ישיר לתהליך הטיפול מול הרופא/ה</li>
            </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            """
            <div class="me-card">
            <h4>🩺 גישת MedExplain המשולבת</h4>
            <ul>
                <li>נתוני מעבדה מובנים מראש בפורמט מוגדר</li>
                <li>סיווג ראשוני דטרמיניסטי, לא תלוי מודל שפה</li>
                <li>הסברים מבוקרים ומוגדרים מראש</li>
                <li>גבולות בטיחות מפורשים ולשון לא-אבחנתית</li>
                <li>מיועד לתמוך בהכנה לשיחה עם הרופא/ה, לא להחליפה</li>
                <li>בעתיד, ניתן לשלב בתשתית מערכת הבריאות עצמה</li>
            </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    ui.render_disclaimer(
        "חשוב להדגיש: אין כאן טענה לפרטיות או לאבטחה מוחלטת. אב-הטיפוס הנוכחי הוא כלי הדגמה "
        "לימודי בלבד. הרעיון המרכזי הוא שמערכת עתידית ומשולבת עשויה לצמצם את הצורך של מטופלים "
        "להדביק מידע רפואי אישי בכלי AI ציבוריים שאינם מיועדים לכך."
    )


def render_safety_page() -> None:
    ui.render_app_header("בטיחות ואתיקה", "הגבולות המפורשים של אב-הטיפוס")

    st.markdown(
        """
        <div class="me-card">
        <h4>מה המערכת כן עושה</h4>
        <ul>
            <li>מספקת הסבר כללי, חינוכי ולא-אבחנתי על תוצאת בדיקה</li>
            <li>מציגה שאלות ממוקדות שיכולות לסייע בשיחה עם הרופא/ה</li>
            <li>משתמשת בסיווג דטרמיניסטי ושקוף מול טווחי ייחוס מוגדרים</li>
        </ul>
        <h4>מה המערכת לא עושה, ולא נועדה לעשות</h4>
        <ul>
            <li>אינה קובעת אבחנה רפואית</li>
            <li>אינה ממליצה על טיפול או תרופה</li>
            <li>אינה מחליפה את הרופא/ה המטפל/ת כסמכות הקלינית הסופית</li>
        </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="me-card">
        <h4>מגבלות ידועות</h4>
        <ul>
            <li><b>סיכון הזיה (hallucination):</b> כל שימוש עתידי ברכיבי AI גנרטיביים דורש
                בקרה קפדנית, שכן טקסט שגוי עלול להיראות משכנע.</li>
            <li><b>סיכון להרגעת יתר:</b> ניסוח רגוע מדי עלול לגרום למטופל להמעיט בחשיבות ממצא.</li>
            <li><b>שונות בין מעבדות:</b> טווחי הייחוס בפועל משתנים בין מעבדות ושיטות מדידה.</li>
            <li><b>הבדלים בין אוכלוסיות:</b> טווחי ייחוס עשויים להשתנות בהתאם לגיל, מין, הריון
                ורקע קליני נוסף שאינו מיוצג באב-הטיפוס.</li>
            <li><b>אוריינות בריאותית:</b> מטופלים שונים זקוקים לרמות שונות של פירוט והסבר.</li>
            <li><b>נגישות ושפה:</b> הממשק הנוכחי מוצג בעברית בלבד, ואינו מותאם לכלל האוכלוסייה.</li>
            <li><b>נדרש אימות קליני:</b> כל תוכן רפואי באב-הטיפוס דורש בדיקה ואישור של גורם
                רפואי מוסמך לפני כל שימוש מעבר להדגמה לימודית.</li>
        </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="me-card">
        <h4>נכונות טכנית לעומת בטיחות קלינית</h4>
        <p>
        חשוב להבחין בין <b>נכונות טכנית</b> — הקוד פועל, הסיווג המספרי תואם את הכללים שהוגדרו —
        לבין <b>בטיחות קלינית</b>, שדורשת אימות רפואי מוסמך, בדיקת מקורות, והתאמה לאוכלוסיית יעד
        אמיתית. אב-טיפוס יכול להיות נכון טכנית מבלי להיות מוכן לשימוש קליני בפועל.
        </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    ui.render_disclaimer("כל הנתונים במערכת סינתטיים בלבד. לא נעשה שימוש במידע רפואי אמיתי כלשהו.")


def render_feedback_page() -> None:
    ui.render_app_header("משוב מהמטופל", "עזרו לנו לשפר את אב-הטיפוס")

    if "feedback_log" not in st.session_state:
        st.session_state["feedback_log"] = []

    with st.form("feedback_form"):
        clarity = st.slider("עד כמה ההסבר היה ברור?", min_value=1, max_value=5, value=3)
        helpfulness = st.slider(
            "האם ההסבר עזר לך להבין את משמעות התוצאה?", min_value=1, max_value=5, value=3
        )
        questions_clarity = st.radio(
            "האם ברור לך יותר מה כדאי לשאול את הרופא?", options=["כן", "חלקית", "לא"], horizontal=True
        )
        anxiety = st.radio(
            "האם ההסבר הפחית את רמת החשש שלך?",
            options=["כן מאוד", "במידה מסוימת", "לא", "לא רלוונטי"],
            horizontal=True,
        )
        would_use = st.radio(
            "האם היית משתמש/ת בכלי כזה באפליקציית קופת החולים?",
            options=["כן", "אולי", "לא"],
            horizontal=True,
        )
        free_text = st.text_area("מה עדיין לא היה ברור?", value="")
        submitted = st.form_submit_button("שליחת משוב", type="primary")

    if submitted:
        st.session_state["feedback_log"].append(
            {
                "clarity": clarity,
                "helpfulness": helpfulness,
                "questions_clarity": questions_clarity,
                "anxiety": anxiety,
                "would_use": would_use,
                "free_text": free_text,
            }
        )
        st.success("תודה על המשוב! המשוב נשמר לצורך הדגמה בלבד במהלך הפעלת האפליקציה הנוכחית.")

    if st.session_state["feedback_log"]:
        st.markdown(f"#### משובים שנשלחו בהפעלה הנוכחית: {len(st.session_state['feedback_log'])}")
        st.caption("המשובים אינם נשמרים לצמיתות — זוהי הדגמה מבוססת session בלבד, ללא בסיס נתונים.")


def render_architecture_page(meta: dict) -> None:
    ui.render_app_header("ארכיטקטורת המערכת", "תיעוד טכני עבור מעריכי הקורס")

    st.markdown("#### זרימת הנתונים במערכת")
    steps = [
        "נתוני מעבדה מובנים (data/lab_tests.json, data/scenarios.json)",
        "אימות קלט (src/classifier.py :: validate_value)",
        "מנוע סיווג דטרמיניסטי (src/classifier.py :: classify_lab_value)",
        "בחירת הסבר ושאלות (src/explainer.py, src/questions.py)",
        "חסמי בטיחות ולשון לא-אבחנתית (מוטמע בתוכן ה-JSON ובשכבת ההסבר)",
        "ממשק מטופל בעברית מלאה, RTL (app.py, src/ui_components.py)",
    ]
    ui.render_architecture_flow(steps)

    st.markdown("#### תפקיד כל רכיב טכנולוגי")
    st.markdown(
        """
        <div class="me-card">
        <ul>
            <li><b>Python</b> — לוגיקת האפליקציה המרכזית: מודל נתונים, סיווג, הסברים וסיכום.</li>
            <li><b>JSON</b> — ידע רפואי ותצורה הניתנים לעריכה (טווחי ייחוס, הסברים, שאלות),
                מופרדים לחלוטין מקוד הפייתון.</li>
            <li><b>Pandas</b> — בניית טבלת התוצאות המובנית ועיבוד נתוני התרחישים.</li>
            <li><b>Streamlit</b> — שכבת האב-טיפוס האינטראקטיבית ולוח המטופל.</li>
            <li><b>CSS / RTL</b> — התאמת הממשק לעברית ולזהות עיצובית של מוצר בריאות דיגיטלי.</li>
            <li><b>GitLab</b> — ניהול גרסאות במהלך הפיתוח בלבד. GitLab אינו חלק מזמן הריצה
                (runtime) של האפליקציה עצמה.</li>
            <li><b>סיוע מודל שפה (LLM)</b> — שימש לפיתוח ניסוח, תוכן והסברים מראש בשלב הבנייה,
                <u>ולא</u> לצורך סיווג קליני בזמן אמת. הסיווג בפועל הוא דטרמיניסטי לחלוטין.</li>
            <li><b>Base44</b> — שימש כשלב עיצוב חזותי מוקדם/מקביל בתהליך הפיתוח של הפרויקט,
                ואינו חלק מהרצת האפליקציה הנוכחית.</li>
        </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### פרטיות ונתונים")
    st.markdown(
        """
        <div class="me-card">
        <ul>
            <li>כל הנתונים באב-הטיפוס סינתטיים בלבד — אין מידע על מטופלים אמיתיים.</li>
            <li>אין חיבור לתיק רפואי אמיתי (EHR) מכל סוג.</li>
            <li>אין שליחת מידע רפואי לשירות LLM חיצוני בזמן ריצת האפליקציה.</li>
        </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### דרישות עתידיות לפריסה בסביבת ייצור (לא מיושמות באב-הטיפוס)")
    st.markdown(
        """
        <div class="me-card">
        <ul>
            <li>אימות משתמשים (Authentication)</li>
            <li>בקרת גישה מבוססת תפקידים (RBAC)</li>
            <li>הצפנה בתעבורה (encryption in transit)</li>
            <li>הצפנה במנוחה (encryption at rest)</li>
            <li>ניהול סודות מאובטח (secrets management)</li>
            <li>לוגים לבקרה (audit logs) ותיעוד גישה</li>
            <li>ניטור (monitoring) שוטף</li>
            <li>צמצום מידע מזהה למינימום הנדרש</li>
            <li>עמידה בדרישות הפרטיות והרגולציה הרלוונטיות בישראל</li>
            <li>סקירת אבטחה פורמלית</li>
        </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if meta.get("sources_note"):
        ui.render_disclaimer(meta["sources_note"])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(
        page_title="MedExplain AI",
        page_icon="🩺",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    ui.inject_global_css()

    try:
        lab_tests = get_lab_tests()
        meta = get_lab_tests_meta()
        scenarios = get_scenarios()
    except DataLoadError as exc:
        st.error(f"שגיאה בטעינת נתוני המערכת: {exc}")
        st.stop()
        return

    if "page" not in st.session_state:
        st.session_state["page"] = PAGES[0]

    with st.sidebar:
        st.markdown("### 🩺 MedExplain AI")
        st.caption("אב-טיפוס לימודי להסבר תוצאות בדיקות דם")
        page = st.radio("ניווט", options=PAGES, index=PAGES.index(st.session_state["page"]))
        st.session_state["page"] = page
        st.divider()
        st.caption("נתונים סינתטיים בלבד · אינו מכשיר רפואי · אינו מהווה ייעוץ רפואי")

    if page == "עמוד הבית":
        render_home_page()
    elif page == "לוח מטופל":
        render_dashboard_page(lab_tests, scenarios)
    elif page == "כיצד זה עובד":
        render_how_it_works_page()
    elif page == "למה לא ChatGPT?":
        render_why_not_chatgpt_page()
    elif page == "בטיחות ואתיקה":
        render_safety_page()
    elif page == "משוב מהמטופל":
        render_feedback_page()
    elif page == "ארכיטקטורת המערכת":
        render_architecture_page(meta)


if __name__ == "__main__":
    main()
