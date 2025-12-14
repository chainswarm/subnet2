from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from evaluation.api.routers import tournaments_router, stats_router


app = FastAPI(
    title="Subnet2 Evaluation API",
    description="Read-only API for tournament evaluation data",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(tournaments_router)
app.include_router(stats_router)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "evaluation-api"}
