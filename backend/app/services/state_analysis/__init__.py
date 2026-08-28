# Importing the model here guarantees it is registered on Base's
# metadata whenever this package is imported (mirrors why
# tests/conftest.py imports app.main early), without requiring a route
# module to reference it -- Workflow A's history table has no API
# route yet.
from app.models.state_analysis_history import StateAnalysisHistory  # noqa: F401
