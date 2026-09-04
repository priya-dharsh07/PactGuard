# backend/app/api/simulate.py
from fastapi import APIRouter
from backend.app.model.schemas import SimulateRequest, SimulateResponse
from backend.app.core.risk_graph import SemanticRiskGraph

router = APIRouter(prefix="/simulate", tags=["Simulator"])

@router.post("", response_model=SimulateResponse)
async def simulate_contract(request: SimulateRequest):
    original_clauses = request.clauses
    adjustments = request.parameter_adjustments

    orig_graph = SemanticRiskGraph.build_graph(original_clauses)
    original_score = orig_graph.systemic_risk_score

    updated_clauses = []
    for c in original_clauses:
        mod = c.model_copy(deep=True)
        cat_lower = mod.clause_type.lower()

        if "liability" in cat_lower and adjustments.get("cap_liability"):
            mod.risk_score = max(10.0, mod.risk_score - 35.0)
            mod.risk_factors.append("Simulated: Explicit mutual liability cap applied")

        if "terminat" in cat_lower and adjustments.get("extend_notice_days"):
            days = adjustments.get("extend_notice_days")
            mod.risk_score = max(10.0, mod.risk_score - 20.0)
            mod.risk_factors.append(f"Simulated: Notice period extended to {days} days")

        if "indemn" in cat_lower and adjustments.get("make_indemnity_mutual"):
            mod.risk_score = max(15.0, mod.risk_score - 25.0)
            mod.risk_factors.append("Simulated: Mutualized indemnification scope")

        if mod.risk_score >= 70:
            mod.risk_level = "CRITICAL"
        elif mod.risk_score >= 50:
            mod.risk_level = "HIGH"
        elif mod.risk_score >= 25:
            mod.risk_level = "MEDIUM"
        else:
            mod.risk_level = "LOW"

        updated_clauses.append(mod)

    new_graph = SemanticRiskGraph.build_graph(updated_clauses)
    new_score = new_graph.systemic_risk_score
    delta = round(new_score - original_score, 1)

    return SimulateResponse(
        original_risk_score=original_score,
        simulated_risk_score=new_score,
        delta=delta,
        risk_level=new_graph.nodes[0]["risk_level"] if new_graph.nodes else "LOW",
        impact_summary=f"Simulated adjustments reduced systemic risk by {abs(delta)} points." if delta < 0 else "Risk level unchanged.",
        updated_clauses=updated_clauses,
        updated_graph=new_graph
    )