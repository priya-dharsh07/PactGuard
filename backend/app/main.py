from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api import contracts, simulate

app = FastAPI(
    title="PactGuard API",
    description="AI-powered contract intelligence & risk analysis",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    contracts.router,
    prefix="/api/contracts",
    tags=["contracts"],
)

app.include_router(
    simulate.router,
    prefix="/api/simulate",
    tags=["simulate"],
)

@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "pactguard-backend",
    }