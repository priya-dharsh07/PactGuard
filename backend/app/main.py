# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api.contracts import router as contracts_router
from backend.app.api.simulate import router as simulate_router
from backend.app.api.llm_features import router as llm_router

app = FastAPI(
    title="PactGuard API",
    description="Open-Vocabulary Contract Intelligence & AI Legal Copilot",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(contracts_router)
app.include_router(simulate_router)
app.include_router(llm_router)

@app.get("/health")
def health_check():
    return {"status": "healthy", "engine": "Flan-T5 Seq2Seq + OpenRouter Legal Copilot"}