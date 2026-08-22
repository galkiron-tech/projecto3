"""
data_loader.py
---------------
Responsible for loading the structured medical knowledge (data/lab_tests.json)
and the synthetic demo scenarios (data/scenarios.json) from disk.

Keeping loading logic in one place means the rest of the application never
touches the filesystem or raw JSON directly -- it works with plain Python
dictionaries / the dataclasses defined in models.py.
"""

from __future__ import annotations

import json
import os
from typing import Any

from src.models import PatientScenario

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
_LAB_TESTS_PATH = os.path.join(_DATA_DIR, "lab_tests.json")
_SCENARIOS_PATH = os.path.join(_DATA_DIR, "scenarios.json")


class DataLoadError(Exception):
    """Raised when a required data file is missing or malformed."""


def load_lab_tests() -> dict[str, Any]:
    """Load and return the `tests` mapping from data/lab_tests.json.

    Returns a dict keyed by test_key (e.g. "wbc", "hba1c", ...) mapping to
    the structured medical knowledge for that test.
    """
    try:
        with open(_LAB_TESTS_PATH, encoding="utf-8") as f:
            raw = json.load(f)
    except FileNotFoundError as exc:
        raise DataLoadError(f"קובץ הגדרות הבדיקות לא נמצא: {_LAB_TESTS_PATH}") from exc
    except json.JSONDecodeError as exc:
        raise DataLoadError("קובץ הגדרות הבדיקות פגום ואינו תקין (JSON invalid).") from exc

    tests = raw.get("tests")
    if not tests:
        raise DataLoadError("קובץ הגדרות הבדיקות אינו מכיל בדיקות.")
    return tests


def load_lab_tests_meta() -> dict[str, Any]:
    """Load the `_meta` block (disclaimers / source notes) from lab_tests.json."""
    try:
        with open(_LAB_TESTS_PATH, encoding="utf-8") as f:
            raw = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return raw.get("_meta", {})


def load_scenarios() -> list[PatientScenario]:
    """Load the synthetic demo scenarios from data/scenarios.json.

    Returns a list of PatientScenario dataclass instances.
    """
    try:
        with open(_SCENARIOS_PATH, encoding="utf-8") as f:
            raw = json.load(f)
    except FileNotFoundError as exc:
        raise DataLoadError(f"קובץ התרחישים לא נמצא: {_SCENARIOS_PATH}") from exc
    except json.JSONDecodeError as exc:
        raise DataLoadError("קובץ התרחישים פגום ואינו תקין (JSON invalid).") from exc

    scenarios_raw = raw.get("scenarios", [])
    scenarios: list[PatientScenario] = []
    for item in scenarios_raw:
        try:
            scenarios.append(
                PatientScenario(
                    id=item["id"],
                    title=item["title"],
                    patient_name=item["patient_name"],
                    age=item["age"],
                    sex=item["sex"],
                    context=item["context"],
                    lab_values=item.get("lab_values", {}),
                    previous_values=item.get("previous_values", {}),
                    notes=item.get("notes"),
                )
            )
        except KeyError:
            # Skip malformed scenario entries rather than crashing the app.
            continue

    if not scenarios:
        raise DataLoadError("לא נמצאו תרחישי הדגמה תקינים בקובץ התרחישים.")

    return scenarios
