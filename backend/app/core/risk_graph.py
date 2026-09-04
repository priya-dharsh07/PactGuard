# backend/app/core/risk_graph.py
import re
from typing import List, Tuple
from backend.app.model.schemas import ClauseAnalysis, RiskGraphData, RiskGraphEdge, ClauseParameters

def extract_clause_parameters(text: str) -> ClauseParameters:
    durations = re.findall(r"\b\d+\s*(?:days?|months?|years?|weeks?|hours?)\b", text, re.IGNORECASE)
    notice = re.findall(r"\b\d+\s*(?:days?|months?|hours?)\s*(?:prior|advance)?\s*written\s*notice\b", text, re.IGNORECASE)
    financials = re.findall(r"(?:\$|USD|EUR|GBP|INR|₹)\s*[\d,]+(?:\.\d+)?|\b\d+%\b", text, re.IGNORECASE)
    
    return ClauseParameters(
        durations=list(set(durations)),
        notice_periods=list(set(notice)),
        financial_terms=list(set(financials))
    )

def evaluate_dynamic_clause_risk(clause_type: str, text: str) -> Tuple[float, str, List[str]]:

    text_lower = text.lower()
    cat_lower = clause_type.lower()
    risk = 20.0  # Base commercial standard
    factors = []

    # 1. Indemnity / Hold Harmless
    if "indemn" in cat_lower or "indemn" in text_lower:
        if "sole" in text_lower or "defend, indemnify, and hold harmless" in text_lower:
            risk += 25.0
            factors.append("Unilateral, broad-form indemnity obligation")
        if "unlimited" in text_lower or "without limitation" in text_lower:
            risk += 35.0
            factors.append("Uncapped indemnity liability exposure")
        if "gross negligence" not in text_lower and "willful misconduct" not in text_lower:
            risk += 15.0
            factors.append("Indemnity not limited to gross negligence or willful misconduct")

    # 2. Limitation of Liability
    if "liability" in cat_lower or "liability" in text_lower:
        if "unlimited" in text_lower or "not apply to" in text_lower or "no cap" in text_lower:
            risk += 40.0
            factors.append("Absence or carve-out from aggregate liability cap")
        elif "shall not exceed" in text_lower:
            risk += 10.0
            factors.append("Capped liability standard clause")

    # 3. Termination / Cancellation
    if "terminat" in cat_lower or "terminat" in text_lower:
        if "convenience" in text_lower:
            if any(d in text_lower for d in ["immediate", "24 hours", "3 days", "7 days"]):
                risk += 35.0
                factors.append("Immediate or ultra-short termination for convenience")
            else:
                risk += 20.0
                factors.append("Unilateral termination for convenience")
        if "without notice" in text_lower:
            risk += 40.0
            factors.append("Termination without cure period or prior notice")

    # 4. Anti-Assignment & Subleasing
    if "assign" in cat_lower or "sublease" in cat_lower or "sublet" in text_lower:
        if "sole discretion" in text_lower or "may not assign" in text_lower:
            risk += 25.0
            factors.append("Strict anti-assignment restriction without reasonable consent standard")

    # 5. Restrictive Covenants / Non-Compete
    if "compete" in cat_lower or "compete" in text_lower or "solicit" in text_lower:
        if any(y in text_lower for y in ["2 years", "3 years", "5 years", "worldwide"]):
            risk += 40.0
            factors.append("Excessive post-termination non-compete duration or geography")
        else:
            risk += 25.0
            factors.append("Post-termination restrictive covenant")

    # 6. Fees & Liquidated Damages
    if "fee" in cat_lower or "payment" in cat_lower or "damage" in cat_lower:
        if "non-refundable" in text_lower or "forfeit" in text_lower:
            risk += 30.0
            factors.append("Strict non-refundable deposit / liquidated damages clause")
        if "compound interest" in text_lower or "penalty" in text_lower:
            risk += 20.0
            factors.append("High late-payment interest penalty")

    risk = max(5.0, min(95.0, round(risk, 1)))

    if risk >= 75.0:
        level = "CRITICAL"
    elif risk >= 50.0:
        level = "HIGH"
    elif risk >= 25.0:
        level = "MEDIUM"
    else:
        level = "LOW"

    if not factors:
        factors.append("Standard commercial clause phrasing")

    return risk, level, factors


class SemanticRiskGraph:
    INTERACTION_PATTERNS = [
        {
            "src": ["indemn", "hold harmless"],
            "tgt": ["liability", "limitation of liability"],
            "relation": "UNPROTECTED_EXPOSURE",
            "multiplier": 1.45,
            "desc": "Indemnity carve-outs may bypass the limitation of liability cap."
        },
        {
            "src": ["terminat", "cancellation"],
            "tgt": ["fee", "payment", "liquidated damages"],
            "relation": "TERMINATION_PENALTY_ACCELERATION",
            "multiplier": 1.30,
            "desc": "Termination triggers immediate acceleration of payments or fee forfeiture."
        },
        {
            "src": ["non-compete", "restrictive covenant"],
            "tgt": ["terminat"],
            "relation": "POST_TERMINATION_RESTRAINT",
            "multiplier": 1.25,
            "desc": "Restrictive covenants remain enforceable post-termination."
        },
        {
            "src": ["confidential", "nda"],
            "tgt": ["indemn"],
            "relation": "CONFIDENTIALITY_INDEMNITY_LOOP",
            "multiplier": 1.20,
            "desc": "Confidentiality breaches carry uncapped indemnification obligations."
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
            edge_boost = sum((e.risk_multiplier - 1.0) * 7.5 for e in edges)
            systemic_score = min(98.0, round(base_avg + edge_boost, 1))

        return RiskGraphData(
            nodes=nodes,
            edges=edges,
            systemic_risk_score=systemic_score
        )