import networkx as nx

from backend.app.models.schemas import Clause, ClauseEdge, ClauseType, RiskLevel

# (clause_type_a, clause_type_b) -> amplification weight (0.0 - 1.0)
CLAUSE_INTERACTIONS: dict[tuple[ClauseType, ClauseType], float] = {
    (ClauseType.INDEMNITY, ClauseType.LIABILITY_CAP): 0.6,
    (ClauseType.TERMINATION, ClauseType.AUTO_RENEWAL): 0.5,
    (ClauseType.CONFIDENTIALITY, ClauseType.GOVERNING_LAW): 0.3,
}


def infer_edges(clauses: list[Clause]) -> list[ClauseEdge]:
    """Look at which clause types are actually present in this contract
    and wire up edges for any known-interacting pair."""
    edges = []
    for i, a in enumerate(clauses):
        for b in clauses[i + 1:]:
            weight = CLAUSE_INTERACTIONS.get((a.clause_type, b.clause_type)) \
                or CLAUSE_INTERACTIONS.get((b.clause_type, a.clause_type))
            if weight:
                edges.append(ClauseEdge(source_id=a.id, target_id=b.id, weight=weight))
    return edges


def compute_compounded_scores(
    clauses: list[Clause], edges: list[ClauseEdge]
) -> dict[str, float]:
    """Return {clause_id: compounded_risk_score} for every clause."""
    graph = nx.Graph()
    for clause in clauses:
        graph.add_node(clause.id, base_score=clause.base_risk_score)
    for edge in edges:
        graph.add_edge(edge.source_id, edge.target_id, weight=edge.weight)

    scores: dict[str, float] = {}
    for clause in clauses:
        base = graph.nodes[clause.id]["base_score"]
        amplification = sum(
            graph.nodes[neighbor]["base_score"] * graph[clause.id][neighbor]["weight"]
            for neighbor in graph.neighbors(clause.id)
        )
        scores[clause.id] = min(1.0, base + amplification)
    return scores


def overall_score(per_clause_scores: dict[str, float]) -> float:
    """Contract-level score: the average of compounded clause scores,
    weighted slightly toward the worst offender so one very bad clause
    can't get diluted by several harmless ones."""
    if not per_clause_scores:
        return 0.0
    values = list(per_clause_scores.values())
    avg = sum(values) / len(values)
    worst = max(values)
    return round(0.5 * avg + 0.5 * worst, 3)


def score_to_level(score: float) -> RiskLevel:
    if score >= 0.66:
        return RiskLevel.HIGH
    if score >= 0.33:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def estimate_exposure(
    clauses: list[Clause], contract_value: float | None
) -> float | None:
    """Very simple, transparent heuristic - not legal advice, just a
    concrete number so the user feels the risk instead of reading a label.
    Uncapped liability/indemnity risk is estimated against the full
    contract value; a capped clause is estimated against its cap."""
    if not contract_value:
        return None
    exposure = 0.0
    for clause in clauses:
        if clause.clause_type in (ClauseType.INDEMNITY, ClauseType.LIABILITY_CAP):
            cap_months = clause.parameters.get("cap_months")
            if cap_months:
                monthly_value = contract_value / 12
                exposure += monthly_value * cap_months
            else:
                exposure += contract_value * clause.base_risk_score
    return round(exposure, 2)
