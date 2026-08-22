"""
explainer.py
-------------
Builds the patient-facing explanation content for a classified lab result.

All wording here follows the safe-language rules of the project:
 - never states a diagnosis
 - always frames deviations as possibilities, not conclusions
 - always points back to the treating physician as the next step

This module only *selects and assembles* pre-written, reviewed text
fragments from data/lab_tests.json -- it does not generate new medical
claims at runtime.
"""

from __future__ import annotations

from typing import Any

from src.models import ClassifiedLabResult

NORMAL_SUMMARY = "הערך נמצא בטווח הייחוס שהוגדר באב-הטיפוס."
BORDERLINE_LOW_SUMMARY = "הערך מעט מתחת לטווח הייחוס המקובל."
BORDERLINE_HIGH_SUMMARY = "הערך מעט מעל לטווח הייחוס המקובל."
ABNORMAL_LOW_SUMMARY = "הערך נמוך מהטווח המקובל."
ABNORMAL_HIGH_SUMMARY = "הערך גבוה מהטווח המקובל."

WHO_TO_CONSULT_DEFAULT = (
    "ברוב המקרים הצעד הראשון הוא פנייה לרופא/ת המשפחה, "
    "שיוכל/תוכל להחליט האם נדרש בירור נוסף או הפניה לגורם מקצועי."
)


def _summary_sentence(result: ClassifiedLabResult) -> str:
    if result.status == "normal":
        return NORMAL_SUMMARY
    if result.status == "borderline":
        return BORDERLINE_LOW_SUMMARY if result.direction == "low" else BORDERLINE_HIGH_SUMMARY
    # abnormal
    return ABNORMAL_LOW_SUMMARY if result.direction == "low" else ABNORMAL_HIGH_SUMMARY


def build_explanation(result: ClassifiedLabResult, lab_tests: dict[str, Any]) -> dict[str, Any]:
    """Build the full explanation block for a single classified result.

    Returns a dict with the keys used directly by the UI layer:
        summary, what_it_measures, possible_reasons (list[str]),
        urgency_text, who_to_consult, status, direction
    """
    test_def = lab_tests.get(result.test_key, {})

    possible_reasons: list[str] = []
    if result.status in ("borderline", "abnormal") and result.direction in ("low", "high"):
        reasons_block = test_def.get("possible_reasons", {})
        possible_reasons = reasons_block.get(result.direction, []) or []

    urgency_text = ""
    if result.status == "borderline":
        urgency_text = test_def.get("urgency_text", {}).get(
            "borderline",
            "לרוב לא מדובר במצב דחוף, אך כדאי לדון בממצא עם הרופא/ה.",
        )
    elif result.status == "abnormal":
        urgency_text = test_def.get("urgency_text", {}).get(
            "abnormal",
            "מומלץ לדון בתוצאה עם רופא/ת המשפחה בהקדם סביר.",
        )

    return {
        "test_key": result.test_key,
        "name_he": result.name_he,
        "status": result.status,
        "direction": result.direction,
        "summary": _summary_sentence(result),
        "what_it_measures": test_def.get("what_it_measures", ""),
        "possible_reasons": possible_reasons,
        "urgency_text": urgency_text,
        "who_to_consult": test_def.get("who_to_consult", WHO_TO_CONSULT_DEFAULT),
    }


def build_explanations(
    results: list[ClassifiedLabResult], lab_tests: dict[str, Any]
) -> list[dict[str, Any]]:
    """Build explanation blocks for every non-normal result.

    Normal results intentionally do not get a full explanation card --
    per the safety rules, we avoid overclaiming ("your metabolism is
    healthy") and simply show them as normal in the results table.
    """
    return [
        build_explanation(r, lab_tests)
        for r in results
        if r.status in ("borderline", "abnormal")
    ]


TREND_TEXT = {
    "up": "עלה לעומת הבדיקה הקודמת",
    "down": "ירד לעומת הבדיקה הקודמת",
    "unchanged": "ללא שינוי לעומת הבדיקה הקודמת",
}


def trend_label(trend: str | None) -> str | None:
    """Return the Hebrew display label for a trend value, or None."""
    if trend is None:
        return None
    return TREND_TEXT.get(trend)
