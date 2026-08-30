from fastapi import FastAPI

from app.routes.agronomics import router as agronomics_router
from app.routes.decision import router as decision_router
from app.routes.optimization import router as optimization_router
from app.routes.reference import router as reference_router
from app.routes.simulator import router as simulator_router
from app.routes.state_analysis import router as state_analysis_router
from app.routes.stress_assessment import router as stress_assessment_router

app = FastAPI(
    title="KAVACH",
    description=(
        "Sustainability-focused agricultural decision-support API. "
        "Phase 0: ICAR reference data ingestion. "
        "Phase 1: agronomic knowledge base. "
        "Phase 2: virtual sensor simulator. "
        "Phase 3: sensor history / state analysis. "
        "Phase 4: evidence-based problem/stress assessment. "
        "Phase 5: decision engine (5A constraint engine / 5B action "
        "prioritization / 5C recommendation validation). "
        "Phase 6: resource-aware quantitative optimization."
    ),
)

app.include_router(reference_router)
app.include_router(agronomics_router)
app.include_router(simulator_router)
app.include_router(state_analysis_router)
app.include_router(stress_assessment_router)
app.include_router(decision_router)
app.include_router(optimization_router)


@app.get("/health")
def health():
    return {"status": "ok"}
