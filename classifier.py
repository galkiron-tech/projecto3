"""
classifier.py
--------------
The deterministic, rule-based classification engine.

Design principle (see README "Why deterministic classification was chosen"):
No language model is involved in deciding whether a laboratory value is
normal, borderline or abnormal. That decision is made entirely by explicit,
inspectable, testable numeric comparisons against the reference ranges
stored in data/lab_tests.json. This keeps the medically load-bearing part
of the system auditable and reproducible.

Pipeline (conceptual):
    patient input -> validation -> structured lab value -> classification
    -> (explanation / question selection happens in other modules)
"""

from __future__ import annotations

from typing import Any, Optional

from src.models import ClassifiedLabResult, LabResult, Sex


class ValidationError(Exception):
    """Raised when a raw patient-entered lab value cannot be safely used."""


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_value(test_key: str, raw_value: Any, lab_tests: dict[str, Any]) -> float:
    """Validate a raw (possibly string) input value for a given test.

    Raises ValidationError with a calm Hebrew message on any problem:
    unknown test, non-numeric input, or a negative/impossible value.
    """
    if test_key not in lab_tests:
        raise ValidationError(f"בדיקה לא מוכרת במערכת: {test_key}")

    if raw_value is None or raw_value == "":
        raise ValidationError("לא הוזן ערך לבדיקה זו.")

    try:
        value = float(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValidationError("הערך שהוזן אינו מספרי. נא להזין מספר בלבד.") from exc

    if value < 0:
        raise ValidationError("לא ניתן להזין ערך שלילי עבור בדיקת מעבדה.")

    # Simple sanity ceiling to catch obvious typos (e.g. an extra digit),
    # generous enough not to reject genuine extreme lab values.
    if value > 100000:
        raise ValidationError("הערך שהוזן חורג מתחום סביר לבדיקת מעבדה. נא לבדוק את הנתון.")

    return value


# ---------------------------------------------------------------------------
# Core classification
# ---------------------------------------------------------------------------

def _resolve_reference(test_def: dict[str, Any], sex: Optional[Sex]) -> dict[str, Any]:
    """Resolve the numeric reference-range dict for a test, given patient sex.

    For sex-specific tests without a known sex, we fall back to the
    female range (the narrower/more conservative of the two in this
    dataset) rather than guessing, and flag that in the returned dict.
    """
    reference = test_def["reference"]
    if not test_def.get("sex_specific"):
        return reference

    if sex in ("male", "female"):
        return reference[sex]

    # Sex unknown: fall back conservatively to the female range so we do not
    # silently under- or over-flag a result. Callers can inspect reference
    # text separately if they want to warn the user sex was not provided.
    return reference.get("female", reference.get("male"))


def _resolve_reference_text(test_def: dict[str, Any], sex: Optional[Sex]) -> str:
    ref_text = test_def.get("reference_text", "")
    if isinstance(ref_text, dict):
        if sex in ("male", "female"):
            return ref_text.get(sex, "")
        return ref_text.get("female", ref_text.get("male", ""))
    return ref_text


def classify_lab_value(
    test_key: str,
    value: float,
    lab_tests: dict[str, Any],
    sex: Optional[Sex] = None,
    age: Optional[int] = None,  # reserved for future age-specific ranges
) -> dict[str, Any]:
    """Classify a single validated numeric lab value.

    Returns a structured dict:
        {
            "status": "normal" | "borderline" | "abnormal",
            "direction": "low" | "high" | "normal",
            "severity": "none" | "mild" | "significant",
            "value": value,
            "unit": unit,
            "reference_text": "...",
            "test_key": test_key,
        }

    This function performs no diagnosis -- it only classifies a value
    against a configured reference range using explicit numeric rules.
    """
    if test_key not in lab_tests:
        raise ValidationError(f"בדיקה לא מוכרת במערכת: {test_key}")

    test_def = lab_tests[test_key]
    ref = _resolve_reference(test_def, sex)
    direction_support = test_def.get("direction", "both")  # "both" | "high_only" | "low_only"

    status = "normal"
    direction = "normal"

    # --- Low side -----------------------------------------------------
    if direction_support in ("both", "low_only"):
        abnormal_low_max = ref.get("abnormal_low_max")
        normal_min = ref.get("normal_min")
        if abnormal_low_max is not None and value < abnormal_low_max:
            status, direction = "abnormal", "low"
        elif normal_min is not None and value < normal_min:
            status, direction = "borderline", "low"

    # --- High side (only checked if low side did not already flag it) --
    if status == "normal" and direction_support in ("both", "high_only"):
        normal_max = ref.get("normal_max")
        abnormal_high_min = ref.get("abnormal_high_min")
        if abnormal_high_min is not None and value >= abnormal_high_min:
            status, direction = "abnormal", "high"
        elif normal_max is not None and value > normal_max:
            status, direction = "borderline", "high"

    severity = "none"
    if status == "borderline":
        severity = "mild"
    elif status == "abnormal":
        severity = "significant"

    return {
        "status": status,
        "direction": direction,
        "severity": severity,
        "value": value,
        "unit": test_def.get("unit", ""),
        "reference_text": _resolve_reference_text(test_def, sex),
        "test_key": test_key,
    }


def compute_trend(value: float, previous_value: Optional[float]) -> Optional[str]:
    """Return 'up' / 'down' / 'unchanged' relative to a previous result.

    Returns None when no previous value is available. This function never
    infers or implies causality -- it only reports numeric direction.
    """
    if previous_value is None:
        return None
    if value > previous_value:
        return "up"
    if value < previous_value:
        return "down"
    return "unchanged"


def classify_patient_results(
    results: list[LabResult],
    lab_tests: dict[str, Any],
    sex: Optional[Sex] = None,
    age: Optional[int] = None,
) -> list[ClassifiedLabResult]:
    """Classify a full set of a patient's entered/scenario lab results.

    Unknown test keys are skipped safely (defensive programming); the UI
    layer is responsible for only ever submitting known test keys.
    """
    classified: list[ClassifiedLabResult] = []

    for result in results:
        if result.test_key not in lab_tests:
            continue

        test_def = lab_tests[result.test_key]
        outcome = classify_lab_value(
            test_key=result.test_key,
            value=result.value,
            lab_tests=lab_tests,
            sex=sex,
            age=age,
        )
        trend = compute_trend(result.value, result.previous_value)

        classified.append(
            ClassifiedLabResult(
                test_key=result.test_key,
                name_he=test_def.get("name_he", result.test_key),
                abbreviation=test_def.get("abbreviation", result.test_key.upper()),
                value=result.value,
                unit=outcome["unit"],
                status=outcome["status"],
                direction=outcome["direction"],
                reference_text=outcome["reference_text"],
                previous_value=result.previous_value,
                trend=trend,
            )
        )

    return classified
