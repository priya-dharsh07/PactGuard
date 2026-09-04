from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ClauseParameters(BaseModel):
    durations: List[str] = Field(default_factory=list, description="Extracted time durations")
    notice_periods: List[str] = Field(default_factory=list, description="Extracted notice requirements")
    financial_terms: List[str] = Field(default_factory=list, description="Extracted monetary amounts & percentages")

class ClauseEntity(BaseModel):
    name: str
    role: Optional[str] = None

class ClauseAnalysis(BaseModel):
    id: str
    clause_text: str
    clause_type: str = Field(..., description="Open-vocabulary AI predicted category")
    raw_category: Optional[str] = None
    confidence: float = 0.0
    
    # Dynamic Risk Assessment
    risk_score: float = Field(..., ge=0.0, le=100.0, description="Dynamic risk score 0-100 based on actual text")
    risk_level: str = Field(..., description="'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'")
    risk_factors: List[str] = Field(default_factory=list, description="Hazards detected from specific clause terms")
    
    # Information Extraction
    obligations: List[str] = Field(default_factory=list)
    parties: List[ClauseEntity] = Field(default_factory=list)
    parameters: ClauseParameters = Field(default_factory=ClauseParameters)

class RiskGraphEdge(BaseModel):
    source: str
    target: str
    relation_type: str
    risk_multiplier: float
    description: str

class RiskGraphData(BaseModel):
    nodes: List[Dict[str, Any]]
    edges: List[RiskGraphEdge]
    systemic_risk_score: float

class ContractAnalysisResponse(BaseModel):
    contract_id: str
    contract_title: str
    inferred_contract_type: str = Field(..., description="Inferred domain e.g. Lease, SaaS, NDA, Education")
    overall_risk_score: float
    overall_risk_level: str
    executive_summary: str
    clauses: List[ClauseAnalysis]
    risk_graph: RiskGraphData
    actionable_recommendations: List[str] = Field(default_factory=list)

class SimulateRequest(BaseModel):
    contract_id: Optional[str] = None
    clauses: List[ClauseAnalysis]
    parameter_adjustments: Dict[str, Any] = Field(default_factory=dict)

class SimulateResponse(BaseModel):
    original_risk_score: float
    simulated_risk_score: float
    delta: float
    risk_level: str
    impact_summary: str
    updated_clauses: List[ClauseAnalysis]
    updated_graph: RiskGraphData