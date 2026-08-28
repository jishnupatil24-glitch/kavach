"""
5B -- Action Prioritization: "among ELIGIBLE actions, which is
prioritized?" Deterministic sort over already-existing Phase 4
ordinals -- NOT an optimizer, no invented weights.

Sort key (lexicographic, first difference wins):
  1. evidence tier   -- corroborated_evidence before weak_evidence
  2. severity score  -- Phase 4's own 0-6 total_score, descending
  3. category key    -- alphabetical, final deterministic tie-break

abnormal_state_duration.days is deliberately EXCLUDED from the sort
key: comparing a Tier-1 (sourced) day-count against a Tier-2 (proxy)
day-count isn't apples-to-apples confidence-wise, and using it as a
ranking number would smuggle a magnitude judgement in without any
approved basis. It stays on the record for display only.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.services.stress_assessment.evidence import STATUS_CORROBORATED_EVIDENCE, ProblemAssessment


@dataclass(frozen=True)
class PriorityAssignment:
    category: str
    priority: int  # 1 = highest
    reason: str


def _sort_key(problem: ProblemAssessment) -> tuple:
    evidence_rank = 0 if problem.status == STATUS_CORROBORATED_EVIDENCE else 1
    severity_score = (
        problem.severity_factors.total_score if problem.severity_factors is not None else -1
    )
    return (evidence_rank, -severity_score, problem.category)


def prioritize(eligible_problems: list[ProblemAssessment]) -> dict[str, PriorityAssignment]:
    ordered = sorted(eligible_problems, key=_sort_key)
    result: dict[str, PriorityAssignment] = {}
    for i, problem in enumerate(ordered, start=1):
        evidence_rank, neg_severity, _ = _sort_key(problem)
        reason = (
            f"evidence={'corroborated_evidence' if evidence_rank == 0 else 'weak_evidence'}, "
            f"severity_score={-neg_severity}/6, category={problem.category!r} (tie-break)"
        )
        result[problem.category] = PriorityAssignment(problem.category, i, reason)
    return result
