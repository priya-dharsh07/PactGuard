"""
POST /api/simulate

The What-If Simulator's backend half. The frontend sends the full set
of clauses/edges from a prior analysis, plus one clause's edited
parameters, and gets back the recalculated compounded score and
exposure - no re-running the NLP pipeline, just re-running the graph
propagation on the updated numbers.
"""
from fastapi import APIRouter

from backend.app.models.schemas import SimulateRequest, SimulateResponse
from nlp.classifier import _apply_parameter_scoring
from backend.app.core.risk_graph import (
    compute_compounded_scores,
    overall_score,
    score_to_level,
    estimate_exposure,
)

router = APIRouter()


@router.post("", response_model=SimulateResponse)
def simulate(request: SimulateRequest) -> SimulateResponse:
    clauses = request.clauses
    for clause in clauses:
        if clause.id == request.edited_clause_id:
            clause.parameters = {**clause.parameters, **request.edited_parameters}
            clause.base_risk_score = _apply_parameter_scoring(
                clause.clause_type, clause.base_risk_score, clause.parameters
            )

    per_clause_scores = compute_compounded_scores(clauses, request.edges)
    contract_score = overall_score(per_clause_scores)

    return SimulateResponse(
        compounded_risk_score=contract_score,
        risk_level=score_to_level(contract_score),
        estimated_exposure=estimate_exposure(clauses, request.contract_value),
        per_clause_scores=per_clause_scores,
    )
