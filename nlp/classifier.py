import re
import uuid

from backend.app.models.schemas import Clause, ClauseType

# Keyword -> clause type. Checked in order; first match wins.
KEYWORD_RULES: list[tuple[re.Pattern, ClauseType, float]] = [
    (re.compile(r"\bindemnif\w*", re.I), ClauseType.INDEMNITY, 0.5),
    (re.compile(r"\blimitation of liability\b|\bliability.{0,20}cap\b", re.I), ClauseType.LIABILITY_CAP, 0.3),
    (re.compile(r"\btermination\b|\bterminate\b", re.I), ClauseType.TERMINATION, 0.3),
    (re.compile(r"\bauto.?renew\w*\b|\bautomatically renew\w*\b", re.I), ClauseType.AUTO_RENEWAL, 0.4),
    (re.compile(r"\bconfidential\w*\b|\bnon.?disclosure\b", re.I), ClauseType.CONFIDENTIALITY, 0.2),
    (re.compile(r"\bgoverning law\b|\bjurisdiction\b", re.I), ClauseType.GOVERNING_LAW, 0.15),
    (re.compile(r"\bpayment\b|\bfees?\b|\binvoice\b", re.I), ClauseType.PAYMENT_TERMS, 0.2),
]

RISK_AMPLIFIERS = re.compile(r"\buncapped\b|\bunlimited\b|\bsole discretion\b|\bwithout limitation\b", re.I)


def classify_clause(text: str) -> tuple[ClauseType, float, dict[str, float]]:
    for pattern, clause_type, base_score in KEYWORD_RULES:
        if pattern.search(text):
            score = base_score
            if RISK_AMPLIFIERS.search(text):
                score = min(1.0, score + 0.35)
            params = extract_parameters(clause_type, text)
            score = _apply_parameter_scoring(clause_type, score, params)
            return clause_type, score, params
    return ClauseType.OTHER, 0.1, {}


def _apply_parameter_scoring(clause_type: ClauseType, score: float, params: dict[str, float]) -> float:
    """Shared with app.api.simulate._adjust_base_score - kept as the
    single source of truth so upload-time and simulate-time scores are
    always computed the same way."""
    if clause_type == ClauseType.LIABILITY_CAP and "cap_months" in params:
        return round(min(1.0, 0.15 + params["cap_months"] * 0.03), 3)
    if clause_type == ClauseType.TERMINATION and "notice_days" in params:
        return round(min(1.0, 0.15 + params["notice_days"] * 0.01), 3)
    return score


def extract_parameters(clause_type: ClauseType, text: str) -> dict[str, float]:
    """Pull out the numeric knobs the What-If Simulator will expose for
    this clause type, if we can find them in the text."""
    params: dict[str, float] = {}
    if clause_type == ClauseType.LIABILITY_CAP:
        match = re.search(r"(\d+)\s*months?", text, re.I)
        if match:
            params["cap_months"] = float(match.group(1))
    if clause_type == ClauseType.TERMINATION:
        match = re.search(r"(\d+)\s*days?\s*(?:notice|prior)", text, re.I)
        if match:
            params["notice_days"] = float(match.group(1))
    if clause_type == ClauseType.AUTO_RENEWAL:
        match = re.search(r"(\d+)\s*(?:day|month|year)s?", text, re.I)
        if match:
            params["renewal_window_days"] = float(match.group(1))
    return params


def classify_clauses(texts: list[str]) -> list[Clause]:
    clauses = []
    for text in texts:
        clause_type, score, params = classify_clause(text)
        clauses.append(Clause(
            id=str(uuid.uuid4())[:8],
            clause_type=clause_type,
            text=text,
            base_risk_score=score,
            parameters=params,
        ))
    return clauses
