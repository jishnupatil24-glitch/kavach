# Importing the model here guarantees it is registered on Base's
# metadata whenever this package is imported (same reason
# app/services/state_analysis/__init__.py does this for
# StateAnalysisHistory) -- Workflow A's history table has no API route
# referencing the model directly.
from app.models.problem_assessment_history import ProblemAssessmentHistory  # noqa: F401
