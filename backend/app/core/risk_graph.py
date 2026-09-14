# backend/app/core/risk_graph.py
import re
from typing import List, Tuple
from backend.app.model.schemas import ClauseAnalysis, RiskGraphData, RiskGraphEdge, ClauseParameters

def extract_clause_parameters(text: str) -> ClauseParameters:
    durations = re.findall(r"\b\d+\s*(?:days?|months?|years?|weeks?|hours?)\b", text, re.IGNORECASE)
    notice = re.findall(r"\b\d+\s*(?:days?|months?|hours?|one month|two months?)\s*(?:prior|advance)?\s*written\s*notice\b", text, re.IGNORECASE)
    financials = re.findall(r"(?:Rs\.?|\$|USD|EUR|GBP|INR|₹)\s*[\d,]+(?:\.\d+)?|\b\d+%\b|\btwo times\b|\bdouble\b", text, re.IGNORECASE)
    
    return ClauseParameters(
        durations=list(set(durations)),
        notice_periods=list(set(notice)),
        financial_terms=list(set(financials))
    )

def evaluate_dynamic_clause_risk(clause_type: str, text: str) -> Tuple[float, str, List[str]]:
    text_lower = text.lower()
    cat_lower = clause_type.lower()
    risk = 15.0  # Clean base commercial floor
    factors = []

    if any(k in text_lower for k in ["two times", "2x", "double the rent", "double rent", "treble"]):
        risk += 60.0
        factors.append("Punitive 200% double-rent penalty on delayed handover / holdover")
    elif any(k in text_lower for k in ["liquidated damages", "penalty", "forfeit", "forfeiture"]):
        risk += 35.0
        factors.append("Strict liquidated damages / penalty forfeiture obligation")
    
    if any(k in text_lower for k in ["legal proceedings", "recovering possession", "initiating legal", "court proceedings"]):
        risk += 20.0
        factors.append("Express reservation of eviction & legal recovery proceedings")

    if any(k in text_lower for k in ["any circumstances whatsoever", "shall not sublet", "shall not assign", "part with the demised"]):
        risk += 40.0
        factors.append("Absolute prohibition on sublease/assignment with zero exception or consent mechanism")
    elif "sole discretion" in text_lower:
        risk += 25.0
        factors.append("Unilateral sole-discretion approval barrier")

    if any(k in text_lower for k in ["security deposit", "deposit shall be refunded"]):
        if any(k in text_lower for k in ["hold possession", "fails to refund", "without payment of rent"]):
            risk += 25.0
            factors.append("Security deposit dispute mechanism: allows rent withholding / possession dispute")
        if any(k in text_lower for k in ["adjusting any dues", "damages caused by", "cost towards damages"]):
            risk += 15.0
            factors.append("Broad deduction scope against tenant security deposit")

    if any(k in text_lower for k in ["enter upon", "right to visit", "inspection", "carry out repairs", "construction"]):
        if any(k in text_lower for k in ["as and when required", "workmen"]):
            risk += 30.0
            factors.append("Intrusive right of entry / potential interference with quiet possession")
        else:
            risk += 15.0
            factors.append("Periodic property inspection right")

    if any(k in text_lower for k in ["free and harmless", "hold harmless", "defend, indemnify", "indemnif"]):
        if any(k in text_lower for k in ["claims, proceedings", "demands, or actions", "third-party"]):
            risk += 25.0
            factors.append("Broad third-party liability / indemnity & harmless defense covenant")
        if any(k in text_lower for k in ["unlimited", "without limitation", "all liabilities"]):
            risk += 30.0
            factors.append("Uncapped indemnity exposure")

    if any(k in text_lower for k in ["terminated before the expiry", "early termination", "termination for convenience"]):
        if any(k in text_lower for k in ["24 hours", "immediate", "7 days"]):
            risk += 40.0
            factors.append("Immediate or ultra-short termination without adequate cure period")
        elif any(k in text_lower for k in ["one month", "30 days", "prior notice"]):
            risk += 20.0
            factors.append("Unilateral early termination by either party upon 1-month notice")

    if any(k in text_lower for k in ["own expense", "responsibility for the tenant", "minor repairs"]):
        risk += 15.0
        factors.append("Maintenance & minor repair cost shifted entirely to tenant")

    if any(k in text_lower for k in ["compound interest", "running cost of elevator", "separately to the owner"]):
        risk += 15.0
        factors.append("Uncapped ancillary utility & maintenance pass-through charges")

    if any(k in text_lower for k in ["civil courts", "exclusive jurisdiction", "arbitration"]):
        risk += 10.0
        factors.append("Binding local civil court dispute jurisdiction")

    risk = max(10.0, min(95.0, round(risk, 1)))

    if risk >= 70.0:
        level = "CRITICAL"
    elif risk >= 50.0:
        level = "HIGH"
    elif risk >= 30.0:
        level = "MEDIUM"
    else:
        level = "LOW"

    if not factors:
        factors.append("Standard balanced commercial terms")

    return risk, level, factors


class SemanticRiskGraph:

    INTERACTION_PATTERNS = [
        {
            "src": ["liquidated damages", "damage", "two times", "penalty"],
            "tgt": ["terminat", "early termination", "expiry"],
            "relation": "HOLDOVER_PENALTY_COMPOUND",
            "multiplier": 1.50,
            "desc": "Post-termination delay triggers punitive 200% double-rent liquidated damages."
        },
        {
            "src": ["sublet", "assign", "anti assignment"],
            "tgt": ["terminat", "legal proceedings"],
            "relation": "UNCONSENTED_TRANSFER_DEFAULT",
            "multiplier": 1.35,
            "desc": "Breach of strict assignment prohibition allows immediate tenancy cancellation & eviction."
        },
        {
            "src": ["security deposit", "deposit"],
            "tgt": ["damage", "minor repairs", "repair"],
            "relation": "DEPOSIT_DEDUCTION_EXPOSURE",
            "multiplier": 1.30,
            "desc": "Broad repair obligations give owner unilateral deduction rights against security deposit."
        },
        {
            "src": ["enter upon", "visit", "inspection"],
            "tgt": ["free and harmless", "quiet possession"],
            "relation": "QUIET_POSSESSION_CONFLICT",
            "multiplier": 1.25,
            "desc": "Frequent inspection and repair entry rights may conflict with quiet possession covenants."
        }
    ]

    @classmethod
    def build_graph(cls, clauses: List[ClauseAnalysis]) -> RiskGraphData:
        nodes = []
        edges: List[RiskGraphEdge] = []

        for c in clauses:
            nodes.append({
                "id": c.id,
                "label": c.clause_type,
                "risk_score": c.risk_score,
                "risk_level": c.risk_level,
                "summary": c.clause_text[:100] + "..." if len(c.clause_text) > 100 else c.clause_text
            })

        for i, src in enumerate(clauses):
            src_str = (src.clause_type + " " + src.clause_text).lower()
            for j, tgt in enumerate(clauses):
                if i >= j:
                    continue
                tgt_str = (tgt.clause_type + " " + tgt.clause_text).lower()

                for pat in cls.INTERACTION_PATTERNS:
                    src_match = any(k in src_str for k in pat["src"])
                    tgt_match = any(k in tgt_str for k in pat["tgt"])
                    rev_src = any(k in tgt_str for k in pat["src"])
                    rev_tgt = any(k in src_str for k in pat["tgt"])

                    if (src_match and tgt_match) or (rev_src and rev_tgt):
                        edges.append(RiskGraphEdge(
                            source=src.id if (src_match and tgt_match) else tgt.id,
                            target=tgt.id if (src_match and tgt_match) else src.id,
                            relation_type=pat["relation"],
                            risk_multiplier=pat["multiplier"],
                            description=pat["desc"]
                        ))
                        break

        if not clauses:
            systemic_score = 0.0
        else:
            base_avg = sum(c.risk_score for c in clauses) / len(clauses)
            edge_boost = sum((e.risk_multiplier - 1.0) * 8.0 for e in edges)
            systemic_score = min(96.0, round(base_avg + edge_boost, 1))

        return RiskGraphData(
            nodes=nodes,
            edges=edges,
            systemic_risk_score=systemic_score
        )