"""
models.py
---------
Lightweight data model for MedExplain AI.

This module defines the core data structures used across the application:
Patient, LabResult, ClassifiedLabResult and PatientScenario.

Using dataclasses (instead of loose dictionaries scattered through the UI)
keeps the shape of the data explicit and makes the rest of the codebase
(classifier, explainer, questions, summary, UI) easier to reason about.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Literal

Sex = Literal["male", "female"]
Status = Literal["normal", "borderline", "abnormal"]
Direction = Literal["low", "high", "normal"]
Trend = Literal["up", "down", "unchanged"]


@dataclass
class Patient:
    """Basic demographic information used for classification context.

    Only age and sex are used by the classification engine today (sex is
    required for tests with sex-specific reference ranges). Name is optional
    and only used for display purposes in demo scenarios.
    """

    age: Optional[int] = None
    sex: Optional[Sex] = None
    name: Optional[str] = None


@dataclass
class LabResult:
    """A single raw laboratory measurement entered by a patient or scenario.

    `previous_value` is optional and only used to power the (optional) trend
    feature -- it never implies causality, only direction of change.
    """

    test_key: str
    value: float
    previous_value: Optional[float] = None


@dataclass
class ClassifiedLabResult:
    """The output of the deterministic rule-based classification engine.

    This is the object that flows into the explanation, question and
    summary layers, and ultimately into the UI.
    """

    test_key: str
    name_he: str
    abbreviation: str
    value: float
    unit: str
    status: Status               # "normal" | "borderline" | "abnormal"
    direction: Direction         # "low" | "high" | "normal"
    reference_text: str
    previous_value: Optional[float] = None
    trend: Optional[Trend] = None


@dataclass
class PatientScenario:
    """A fully synthetic demonstration patient used in Mode A of the app."""

    id: str
    title: str
    patient_name: str
    age: int
    sex: Sex
    context: str
    lab_values: dict = field(default_factory=dict)
    previous_values: dict = field(default_factory=dict)
    notes: Optional[str] = None
