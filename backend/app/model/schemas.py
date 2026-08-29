from enum import Enum
from typing import Optional
from pydantic import BaseModel


class ClauseType(str, Enum):
    INDEMNITY = "indemnity"
    LIABILITY_CAP = "liability_cap"
    TERMINATION = "termination"
    AUTO_RENEWAL = "auto_renewal"
    CONFIDENTIALITY = "confidentiality"
    GOVERNING_LAW = "governing_law"
    PAYMENT_TERMS = "payment_terms"
    OTHER = "other"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Clause(BaseModel):
    id: str
    clause_type: ClauseType
    text: str
    base_risk_score: float  # 0.0 - 1.0, set by the classifier
    # Editable parameters this clause exposes to the What-If Simulator.
    # e.g. a liability_cap clause exposes {"cap_months": 12}
    parameters: dict[str, float] = {}


class ClauseEdge(BaseModel):
    """An interaction between two clauses that compounds risk."""
    source_id: str
    target_id: str
    weight: float  # 0.0 - 1.0, how strongly they amplify each other


class ContractAnalysis(BaseModel):
    contract_id: str
    contract_value: Optional[float] = None
    clauses: list[Clause]
    edges: list[ClauseEdge]
    compounded_risk_score: float
    risk_level: RiskLevel
    estimated_exposure: Optional[float] = None


class SimulateRequest(BaseModel):
    contract_id: str
    clauses: list[Clause]
    edges: list[ClauseEdge]
    contract_value: Optional[float] = None
    # The single clause the user just edited, with its new parameters
    edited_clause_id: str
    edited_parameters: dict[str, float]


class SimulateResponse(BaseModel):
    compounded_risk_score: float
    risk_level: RiskLevel
    estimated_exposure: Optional[float] = None
    per_clause_scores: dict[str, float]
