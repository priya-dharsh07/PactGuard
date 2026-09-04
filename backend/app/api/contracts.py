# backend/app/api/contracts.py
import io
import re
import uuid
from typing import List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
import pypdf
import docx

from backend.app.model.schemas import ContractAnalysisResponse, ClauseAnalysis
from backend.app.core.risk_graph import (
    evaluate_dynamic_clause_risk,
    extract_clause_parameters,
    SemanticRiskGraph
)
from nlp.inference.predict import get_predictor

router = APIRouter(prefix="/contracts", tags=["Contracts"])

class ContractAnalysisRequest(BaseModel):
    title: Optional[str] = "Uploaded Contract"
    raw_text: str

def infer_contract_type(text: str, title: str = "") -> str:
    """Infers contract domain automatically."""
    sample = (title + " " + text[:2500]).lower()
    if any(k in sample for k in ["land purchase", "real property", "parcel", "deed", "earnest money", "lease", "tenant", "landlord", "premises"]):
        return "Real Estate & Land Acquisition Agreement"
    elif any(k in sample for k in ["non-disclosure", "confidentiality agreement", "disclosing party", "trade secret"]):
        return "Non-Disclosure Agreement (NDA)"
    elif any(k in sample for k in ["saas", "software as a service", "subscription", "cloud service", "license"]):
        return "SaaS & Software License Agreement"
    elif any(k in sample for k in ["employment", "employee", "salary", "job title", "non-compete"]):
        return "Employment Agreement"
    elif any(k in sample for k in ["tuition", "student", "enrollment", "university", "course fee"]):
        return "Educational / Enrollment Agreement"
    elif any(k in sample for k in ["services agreement", "statement of work", "contractor", "client"]):
        return "Master Services Agreement (MSA)"
    else:
        return "Commercial Legal Contract"

def split_into_clauses(text: str) -> List[str]:
    """Splits raw contract text into structured clause chunks and removes page headers/footers."""
    paragraphs = re.split(r"\n\s*\n|(?<=\.)\s*(?=[0-9]+\.\s+[A-Z])", text)
    cleaned = []
    
    ignore_patterns = [
        r"^page\s+\d+(\s+of\s+\d+)?$",
        r"^sample\s+document$",
        r"^witness\s+\d+:",
        r"^_{3,}$",
        r"^date:\s*_{3,}$",
        r"^signature:\s*_{3,}$",
        r"^printed name:\s*_{3,}$"
    ]
    
    for p in paragraphs:
        p_str = p.strip()
        if len(p_str) < 35:
            continue
        if any(re.search(pat, p_str, re.I) for pat in ignore_patterns):
            continue
        cleaned.append(p_str)
        
    if not cleaned and text.strip():
        cleaned = [text.strip()]
    return cleaned

@router.post("/upload")
async def upload_contract_file(file: UploadFile = File(...)):
    """
    Extracts text from uploaded .pdf, .docx, .doc, or .txt files.
    """
    filename = file.filename or "uploaded_contract"
    content = await file.read()
    extracted_text = ""

    # 1. Handle PDF
    if filename.lower().endswith(".pdf"):
        try:
            pdf_reader = pypdf.PdfReader(io.BytesIO(content))
            pages_text = []
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    pages_text.append(text)
            extracted_text = "\n\n".join(pages_text)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse PDF: {str(e)}")

    # 2. Handle DOCX
    elif filename.lower().endswith(".docx"):
        try:
            doc = docx.Document(io.BytesIO(content))
            extracted_text = "\n\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse DOCX: {str(e)}")

    # 3. Handle Plain Text (.txt, .md)
    else:
        try:
            extracted_text = content.decode("utf-8")
        except UnicodeDecodeError:
            extracted_text = content.decode("latin-1", errors="ignore")

    if not extracted_text.strip():
        raise HTTPException(status_code=400, detail="The uploaded document appears to be empty or contains scanned images without text.")

    clean_title = re.sub(r"\.[^/.]+$", "", filename).replace("_", " ").replace("-", " ").title()

    return {
        "filename": filename,
        "title": clean_title,
        "text": extracted_text.strip()
    }


@router.post("/analyze", response_model=ContractAnalysisResponse)
async def analyze_contract(request: ContractAnalysisRequest):
    raw_text = request.raw_text.strip()
    if not raw_text:
        raise HTTPException(status_code=400, detail="Contract text cannot be empty.")

    contract_id = f"cnt_{uuid.uuid4().hex[:8]}"
    inferred_type = infer_contract_type(raw_text, request.title or "")
    clause_texts = split_into_clauses(raw_text)

    predictor = get_predictor()
    clauses: List[ClauseAnalysis] = []

    for idx, c_text in enumerate(clause_texts):
        # 1. AI Inference from fine-tuned Flan-T5
        pred = predictor.predict_clause(c_text)

        # 2. Dynamic Risk Calculation
        risk_score, risk_lvl, risk_factors = evaluate_dynamic_clause_risk(pred["clause_type"], c_text)

        # 3. Parameter Extraction
        params = extract_clause_parameters(c_text)

        clauses.append(ClauseAnalysis(
            id=f"cl_{idx+1}",
            clause_text=c_text,
            clause_type=pred["clause_type"],
            raw_category=pred["raw_category"],
            confidence=pred["confidence"],
            risk_score=risk_score,
            risk_level=risk_lvl,
            risk_factors=risk_factors,
            parameters=params,
            obligations=[f"Comply with terms in {pred['clause_type']}"],
            parties=[]
        ))

    # 4. Build Risk Graph
    graph_data = SemanticRiskGraph.build_graph(clauses)
    overall_score = graph_data.systemic_risk_score

    if overall_score >= 70:
        overall_lvl = "CRITICAL"
    elif overall_score >= 50:
        overall_lvl = "HIGH"
    elif overall_score >= 25:
        overall_lvl = "MEDIUM"
    else:
        overall_lvl = "LOW"

    recommendations = []
    high_risks = [c for c in clauses if c.risk_level in ["HIGH", "CRITICAL"]]
    if high_risks:
        recommendations.append(f"Negotiate caps or notice periods on {len(high_risks)} high-risk clauses.")
    if graph_data.edges:
        recommendations.append(f"Review {len(graph_data.edges)} compound cross-clause liabilities.")

    return ContractAnalysisResponse(
        contract_id=contract_id,
        contract_title=request.title or "Uploaded Contract",
        inferred_contract_type=inferred_type,
        overall_risk_score=overall_score,
        overall_risk_level=overall_lvl,
        executive_summary=f"Identified as '{inferred_type}' with {len(clauses)} clauses. Overall composite risk is {overall_lvl} ({overall_score}/100).",
        clauses=clauses,
        risk_graph=graph_data,
        actionable_recommendations=recommendations
    )