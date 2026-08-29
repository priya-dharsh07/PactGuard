import uuid

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from backend.app.models.schemas import ContractAnalysis
from nlp.extractor import extract_text, split_into_clauses
from nlp.classifier import classify_clauses
from backend.app.core.risk_graph import (
    infer_edges,
    compute_compounded_scores,
    overall_score,
    score_to_level,
    estimate_exposure,
)

router = APIRouter()


@router.post("/upload", response_model=ContractAnalysis)
async def upload_contract(
    file: UploadFile = File(...),
    contract_value: float | None = Form(default=None),
):
    if not file.filename.lower().endswith((".pdf", ".txt")):
        raise HTTPException(status_code=400, detail="Upload a .pdf or .txt file")

    file_bytes = await file.read()
    raw_text = extract_text(file_bytes, file.filename)
    chunks = split_into_clauses(raw_text)

    if not chunks:
        raise HTTPException(
            status_code=422,
            detail="Couldn't find any clause-sized text in this file - "
                   "check it's a text-based (not scanned/image) PDF.",
        )

    clauses = classify_clauses(chunks)
    edges = infer_edges(clauses)
    per_clause_scores = compute_compounded_scores(clauses, edges)
    contract_score = overall_score(per_clause_scores)

    return ContractAnalysis(
        contract_id=str(uuid.uuid4())[:8],
        contract_value=contract_value,
        clauses=clauses,
        edges=edges,
        compounded_risk_score=contract_score,
        risk_level=score_to_level(contract_score),
        estimated_exposure=estimate_exposure(clauses, contract_value),
    )
