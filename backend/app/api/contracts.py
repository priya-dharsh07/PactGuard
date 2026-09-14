import io
import re
import uuid
from typing import List, Optional, Dict
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

    sample = (title + "\n" + text[:4000]).lower()

    domain_scores: Dict[str, float] = {
        "Employment & Labor Agreement": 0.0,
        "Real Estate & Lease Agreement": 0.0,
        "Non-Disclosure Agreement (NDA)": 0.0,
        "SaaS & Software License Agreement": 0.0,
        "Educational & Enrollment Agreement": 0.0,
        "Master Services Agreement (MSA)": 0.0,
        "Loan & Credit Agreement": 0.0,
        "Sales & Procurement Contract": 0.0,
    }

    if re.search(r"\b(employee|employer|employment\s+agreement|contract\s+of\s+employment)\b", sample):
        domain_scores["Employment & Labor Agreement"] += 6.0
    if re.search(r"\b(probation|probationary|salary\s+of|monthly\s+wage|provident\s+fund|gratuity|job\s+responsibilities|duties\s+and\s+responsibilities|labour\s+and\s+employment)\b", sample):
        domain_scores["Employment & Labor Agreement"] += 4.0

    if re.search(r"\b(tenant|landlord|leased\s+premises|demised\s+premises|rental\s+agreement|lease\s+agreement|land\s+purchase|sublet|sublease|monthly\s+rent)\b", sample):
        domain_scores["Real Estate & Lease Agreement"] += 6.0
    if re.search(r"\b(security\s+deposit|earnest\s+money|parcel\s+id|property\s+tax|vacation\s+of\s+the\s+property)\b", sample):
        domain_scores["Real Estate & Lease Agreement"] += 4.0

    if re.search(r"\b(non-disclosure|confidentiality\s+agreement|nda\b|proprietary\s+information)\b", sample):
        domain_scores["Non-Disclosure Agreement (NDA)"] += 6.0
    if re.search(r"\b(disclosing\s+party|receiving\s+party|trade\s+secrets?|confidential\s+information)\b", sample):
        domain_scores["Non-Disclosure Agreement (NDA)"] += 4.0

    if re.search(r"\b(software\s+as\s+a\s+service|saas|software\s+license|api\s+license|cloud\s+service)\b", sample):
        domain_scores["SaaS & Software License Agreement"] += 6.0
    if re.search(r"\b(uptime|sla\b|service\s+level|subscription\s+fees?|end\s+user\s+license)\b", sample):
        domain_scores["SaaS & Software License Agreement"] += 4.0

    if re.search(r"\b(student|tuition|academic\s+semester|enrollment\s+agreement|university|school)\b", sample):
        domain_scores["Educational & Enrollment Agreement"] += 6.0
    if re.search(r"\b(course\s+fee|tuition\s+fees?|academic\s+year|non-refundable\s+tuition)\b", sample):
        domain_scores["Educational & Enrollment Agreement"] += 4.0

    if re.search(r"\b(master\s+services\s+agreement|statement\s+of\s+work|sow\b|independent\s+contractor)\b", sample):
        domain_scores["Master Services Agreement (MSA)"] += 6.0
    if re.search(r"\b(deliverables|consulting\s+services|client\s+and\s+contractor)\b", sample):
        domain_scores["Master Services Agreement (MSA)"] += 4.0

    if re.search(r"\b(loan\s+agreement|promissory\s+note|borrower|lender|credit\s+facility)\b", sample):
        domain_scores["Loan & Credit Agreement"] += 6.0

    if re.search(r"\b(bill\s+of\s+sale|purchase\s+order|sale\s+of\s+goods|buyer\s+and\s+seller)\b", sample):
        domain_scores["Sales & Procurement Contract"] += 6.0

    best_domain, max_score = max(domain_scores.items(), key=lambda x: x[1])
    if max_score >= 3.0:
        return best_domain
    return "Commercial Legal Contract"


def split_into_clauses(text: str) -> List[str]:
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
    filename = file.filename or "uploaded_contract"
    content = await file.read()
    extracted_text = ""

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

    elif filename.lower().endswith(".docx"):
        try:
            doc = docx.Document(io.BytesIO(content))
            extracted_text = "\n\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse DOCX: {str(e)}")

    else:
        try:
            extracted_text = content.decode("utf-8")
        except UnicodeDecodeError:
            extracted_text = content.decode("latin-1", errors="ignore")

    if not extracted_text.strip():
        raise HTTPException(status_code=400, detail="The document appears to be empty or unreadable.")

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
        pred = predictor.predict_clause(c_text)
        risk_score, risk_lvl, risk_factors = evaluate_dynamic_clause_risk(pred["clause_type"], c_text)
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

    graph_data = SemanticRiskGraph.build_graph(clauses)
    overall_score = graph_data.systemic_risk_score

    if overall_score >= 70:
        overall_lvl = "CRITICAL"
    elif overall_score >= 50:
        overall_lvl = "HIGH"
    elif overall_score >= 30:
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