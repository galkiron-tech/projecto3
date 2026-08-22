"""
summary.py
-----------
Builds a structured, non-diagnostic patient summary from a set of
classified lab results.

The summary counts normal / borderline / abnormal results and produces a
single calm, Hebrew summary sentence. It never diagnoses and never claims
that a normal panel proves general health (see safety rules in the brief).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.models import ClassifiedLabResult

ALL_NORMAL_TEXT = "כל הערכים שנבדקו נמצאים בטווחי הייחוס שהוגדרו באב-הטיפוס."


@dataclass
class PatientSummary:
    total_tests: int
    normal_count: int
    borderline_count: int
    abnormal_count: int
    key_findings: list[str] = field(default_factory=list)
    multiple_findings_note: str | None = None
    headline: str = ""


def build_summary(results: list[ClassifiedLabResult]) -> PatientSummary:
    """Aggregate classified results into a structured, non-diagnostic summary."""
    total = len(results)
    normal = [r for r in results if r.status == "normal"]
    borderline = [r for r in results if r.status == "borderline"]
    abnormal = [r for r in results if r.status == "abnormal"]

    key_findings = [r.name_he for r in (abnormal + borderline)]

    multiple_findings_note = None
    non_normal = abnormal + borderline
    if len(non_normal) >= 2:
        names = " ו".join([", ".join(key_findings[:-1]), key_findings[-1]]) if len(key_findings) > 1 else key_findings[0]
        multiple_findings_note = (
            f"נמצאו {len(non_normal)} תוצאות שכדאי לדון בהן עם רופא/ת המשפחה: {names}. "
            "יש לבחון את הממצאים יחד עם התסמינים, ההיסטוריה הרפואית ובדיקות קודמות, "
            "ולא כל ממצא בנפרד."
        )

    if total == 0:
        headline = "לא הוזנו תוצאות בדיקה לניתוח."
    elif len(non_normal) == 0:
        headline = ALL_NORMAL_TEXT
    elif len(non_normal) == 1:
        r = non_normal[0]
        word = "גבולית" if r.status == "borderline" else "חריגה"
        headline = f"נמצאה תוצאה אחת {word} שכדאי לדון בה עם רופא/ת המשפחה: {r.name_he}."
    else:
        headline = multiple_findings_note or ""

    return PatientSummary(
        total_tests=total,
        normal_count=len(normal),
        borderline_count=len(borderline),
        abnormal_count=len(abnormal),
        key_findings=key_findings,
        multiple_findings_note=multiple_findings_note,
        headline=headline,
    )
