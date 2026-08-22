"""
questions.py
-------------
Selects patient-specific "what should I ask my doctor" questions.

Questions are never generated freely by an LLM at runtime -- they are
selected deterministically from the reviewed question_templates stored in
data/lab_tests.json, based on:
  - which test(s) are borderline/abnormal
  - combinations of tests that are clinically often discussed together
    (e.g. WBC + CRP, Hemoglobin + Ferritin)
  - simple contextual keywords in the scenario notes (e.g. "recent illness",
    "vegetarian") that are provided by the scenario/patient, not inferred.

This keeps question selection auditable: every possible question a patient
sees was written and reviewed in advance.
"""

from __future__ import annotations

from typing import Any, Optional

from src.models import ClassifiedLabResult

# Test-key pairs that, when both flagged, warrant a combined question set
# instead of (or in addition to) the individual per-test questions.
_COMBO_PAIRS = [
    {"tests": {"wbc", "crp"}, "trigger_key": "combo_with_wbc_high", "owner_key": "crp"},
    {"tests": {"hemoglobin", "ferritin"}, "trigger_key": "combo_with_ferritin_low", "owner_key": "hemoglobin"},
    {"tests": {"hemoglobin", "ferritin"}, "trigger_key": "combo_with_hemoglobin_low", "owner_key": "ferritin"},
]


def _flagged_keys(results: list[ClassifiedLabResult]) -> set[str]:
    return {r.test_key for r in results if r.status in ("borderline", "abnormal")}


def _notes_context_key(test_key: str, notes: Optional[str]) -> Optional[str]:
    """Very small, explicit keyword mapping from scenario notes to a
    specific question-template variant. This is intentionally simple and
    transparent rather than an inferred/guessed classification.
    """
    if not notes:
        return None
    lowered = notes.strip()

    if test_key == "wbc" and ("ויראלית" in lowered or "מחלה" in lowered or "שפעת" in lowered):
        return "recent_illness"
    if test_key == "ferritin" and ("צמחוני" in lowered or "טבעוני" in lowered):
        return "vegetarian_context"
    return None


def select_questions_for_result(
    result: ClassifiedLabResult,
    lab_tests: dict[str, Any],
    notes: Optional[str] = None,
) -> list[str]:
    """Select the question list for a single flagged result (no combos)."""
    test_def = lab_tests.get(result.test_key, {})
    templates = test_def.get("question_templates", {})

    context_key = _notes_context_key(result.test_key, notes)
    if context_key and context_key in templates:
        return list(templates[context_key])

    return list(templates.get("general", []))


def select_questions(
    results: list[ClassifiedLabResult],
    lab_tests: dict[str, Any],
    notes: Optional[str] = None,
) -> dict[str, list[str]]:
    """Select physician questions for a full set of classified results.

    Returns a dict mapping a display label (test name, or a combined label)
    to its list of questions. Tests that participate in a combo are grouped
    under a single combined entry rather than duplicated individually.
    """
    flagged = [r for r in results if r.status in ("borderline", "abnormal")]
    flagged_keys = _flagged_keys(results)

    used_in_combo: set[str] = set()
    output: dict[str, list[str]] = {}

    for combo in _COMBO_PAIRS:
        if combo["tests"].issubset(flagged_keys):
            owner_key = combo["owner_key"]
            owner_def = lab_tests.get(owner_key, {})
            templates = owner_def.get("question_templates", {})
            trigger_key = combo["trigger_key"]
            if trigger_key in templates:
                label_keys = sorted(combo["tests"])
                labels_he = " + ".join(
                    lab_tests.get(k, {}).get("abbreviation", k) for k in label_keys
                )
                output[labels_he] = list(templates[trigger_key])
                used_in_combo.update(combo["tests"])

    for result in flagged:
        if result.test_key in used_in_combo:
            continue
        questions = select_questions_for_result(result, lab_tests, notes)
        if questions:
            output[result.name_he] = questions

    return output


def select_questions_by_test(
    results: list[ClassifiedLabResult],
    lab_tests: dict[str, Any],
    notes: Optional[str] = None,
) -> dict[str, list[str]]:
    """Same selection logic as `select_questions`, but keyed by test_key
    instead of display label -- convenient when rendering one explanation
    card per test while still sharing a combined question set for tests
    that participate in a combo (e.g. WBC + CRP share one list).
    """
    flagged_keys = _flagged_keys(results)
    by_test: dict[str, list[str]] = {}
    used_in_combo: set[str] = set()

    for combo in _COMBO_PAIRS:
        if combo["tests"].issubset(flagged_keys):
            owner_def = lab_tests.get(combo["owner_key"], {})
            templates = owner_def.get("question_templates", {})
            trigger_key = combo["trigger_key"]
            if trigger_key in templates:
                questions = list(templates[trigger_key])
                for key in combo["tests"]:
                    by_test[key] = questions
                used_in_combo.update(combo["tests"])

    for result in results:
        if result.status not in ("borderline", "abnormal"):
            continue
        if result.test_key in used_in_combo:
            continue
        by_test[result.test_key] = select_questions_for_result(result, lab_tests, notes)

    return by_test
