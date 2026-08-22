"""MedExplain AI -- application source package.

Modules:
    models        Core dataclasses (Patient, LabResult, ClassifiedLabResult, PatientScenario)
    data_loader   Loads structured medical knowledge and demo scenarios from JSON
    classifier    Deterministic rule-based lab-value classification engine
    explainer     Builds patient-facing, non-diagnostic explanation text
    questions     Selects scenario-specific physician questions
    summary       Builds the aggregated patient summary
    ui_components Streamlit rendering helpers / RTL styling
"""
