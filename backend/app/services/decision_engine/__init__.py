# Importing the model here guarantees it is registered on Base's
# metadata whenever this package is imported (same reason
# app/services/stress_assessment/__init__.py does this for
# ProblemAssessmentHistory) -- Workflow A's history table has no API
# route referencing the model directly.
from app.models.decision_history import DecisionHistory  # noqa: F401
