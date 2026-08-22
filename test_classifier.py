"""
tests/test_classifier.py
--------------------------
Unit tests for the deterministic rule-based classification engine
(src/classifier.py). These tests exist to demonstrate that laboratory
classification is reproducible and does not depend on any language model.
"""

import os
import sys

# Ensure the project root is importable regardless of how pytest is invoked.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from src.classifier import (
    ValidationError,
    classify_lab_value,
    classify_patient_results,
    compute_trend,
    validate_value,
)
from src.data_loader import load_lab_tests
from src.models import LabResult


@pytest.fixture(scope="module")
def lab_tests():
    return load_lab_tests()


# ---------------------------------------------------------------------------
# HbA1c classification
# ---------------------------------------------------------------------------

def test_hba1c_normal(lab_tests):
    result = classify_lab_value("hba1c", 5.2, lab_tests)
    assert result["status"] == "normal"
    assert result["direction"] == "normal"


def test_hba1c_borderline(lab_tests):
    result = classify_lab_value("hba1c", 6.0, lab_tests)
    assert result["status"] == "borderline"
    assert result["direction"] == "high"


def test_hba1c_elevated_abnormal(lab_tests):
    result = classify_lab_value("hba1c", 7.1, lab_tests)
    assert result["status"] == "abnormal"
    assert result["direction"] == "high"


def test_hba1c_boundary_exactly_at_abnormal_threshold(lab_tests):
    # 6.5 is defined as the abnormal threshold (>=), so it should be abnormal.
    result = classify_lab_value("hba1c", 6.5, lab_tests)
    assert result["status"] == "abnormal"


# ---------------------------------------------------------------------------
# WBC classification
# ---------------------------------------------------------------------------

def test_wbc_normal(lab_tests):
    result = classify_lab_value("wbc", 6.5, lab_tests)
    assert result["status"] == "normal"


def test_wbc_elevated_borderline(lab_tests):
    result = classify_lab_value("wbc", 10.4, lab_tests)
    assert result["status"] == "borderline"
    assert result["direction"] == "high"


def test_wbc_elevated_abnormal(lab_tests):
    result = classify_lab_value("wbc", 12.8, lab_tests)
    assert result["status"] == "abnormal"
    assert result["direction"] == "high"


def test_wbc_low_abnormal(lab_tests):
    result = classify_lab_value("wbc", 3.0, lab_tests)
    assert result["status"] == "abnormal"
    assert result["direction"] == "low"


# ---------------------------------------------------------------------------
# Sex-specific classification (hemoglobin, ferritin, HDL)
# ---------------------------------------------------------------------------

def test_hemoglobin_female_abnormal_low(lab_tests):
    result = classify_lab_value("hemoglobin", 10.4, lab_tests, sex="female")
    assert result["status"] == "abnormal"
    assert result["direction"] == "low"


def test_hemoglobin_male_normal(lab_tests):
    result = classify_lab_value("hemoglobin", 15.0, lab_tests, sex="male")
    assert result["status"] == "normal"


def test_hemoglobin_same_value_different_sex_can_differ(lab_tests):
    # 12.2 g/dL is within the normal female range but below the normal
    # male range -- demonstrating that sex-specific reference ranges
    # genuinely change the classification outcome.
    female_result = classify_lab_value("hemoglobin", 12.2, lab_tests, sex="female")
    male_result = classify_lab_value("hemoglobin", 12.2, lab_tests, sex="male")
    assert female_result["status"] == "normal"
    assert male_result["status"] in ("borderline", "abnormal")


def test_hdl_low_only_direction_never_flags_high(lab_tests):
    # HDL is a "low_only" direction test -- a very high value should never
    # be classified as abnormal/borderline, since higher HDL is protective.
    result = classify_lab_value("hdl", 95, lab_tests, sex="male")
    assert result["status"] == "normal"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def test_validate_value_missing_raises(lab_tests):
    with pytest.raises(ValidationError):
        validate_value("wbc", "", lab_tests)


def test_validate_value_none_raises(lab_tests):
    with pytest.raises(ValidationError):
        validate_value("wbc", None, lab_tests)


def test_validate_value_non_numeric_raises(lab_tests):
    with pytest.raises(ValidationError):
        validate_value("wbc", "abc", lab_tests)


def test_validate_value_negative_raises(lab_tests):
    with pytest.raises(ValidationError):
        validate_value("wbc", "-5", lab_tests)


def test_validate_value_unknown_test_raises(lab_tests):
    with pytest.raises(ValidationError):
        validate_value("not_a_real_test", "5", lab_tests)


def test_validate_value_valid_numeric_string(lab_tests):
    value = validate_value("wbc", "6.5", lab_tests)
    assert value == 6.5


def test_classify_lab_value_unknown_test_raises(lab_tests):
    with pytest.raises(ValidationError):
        classify_lab_value("not_a_real_test", 5.0, lab_tests)


# ---------------------------------------------------------------------------
# Trend computation (no causality claims, only direction)
# ---------------------------------------------------------------------------

def test_compute_trend_up():
    assert compute_trend(7.0, 6.5) == "up"


def test_compute_trend_down():
    assert compute_trend(5.5, 6.0) == "down"


def test_compute_trend_unchanged():
    assert compute_trend(5.5, 5.5) == "unchanged"


def test_compute_trend_no_previous_value_returns_none():
    assert compute_trend(5.5, None) is None


# ---------------------------------------------------------------------------
# Full patient-result classification pipeline
# ---------------------------------------------------------------------------

def test_classify_patient_results_deterministic_and_repeatable(lab_tests):
    results = [
        LabResult(test_key="hba1c", value=7.1),
        LabResult(test_key="wbc", value=6.5),
    ]
    first_pass = classify_patient_results(results, lab_tests, sex="female", age=40)
    second_pass = classify_patient_results(results, lab_tests, sex="female", age=40)

    statuses_first = [r.status for r in first_pass]
    statuses_second = [r.status for r in second_pass]
    assert statuses_first == statuses_second
    assert statuses_first == ["abnormal", "normal"]


def test_classify_patient_results_skips_unknown_test_keys(lab_tests):
    results = [
        LabResult(test_key="wbc", value=6.5),
        LabResult(test_key="not_a_real_test", value=1.0),
    ]
    classified = classify_patient_results(results, lab_tests, sex="male")
    assert len(classified) == 1
    assert classified[0].test_key == "wbc"


def test_classify_patient_results_empty_list_returns_empty(lab_tests):
    assert classify_patient_results([], lab_tests) == []
