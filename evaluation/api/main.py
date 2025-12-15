"""
Subnet Analytics Tournaments API.

Pattern detection & feature generation evaluation platform.

Future tournament types:
- ML Tournaments: Machine learning model evaluation
- LLM Tournaments: Language model evaluation
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from evaluation.api.routers import (
    analytics_tournaments_router,
    analytics_stats_router,
)


# OpenAPI tags for grouping endpoints
tags_metadata = [
    {
        "name": "Tournaments",
        "description": """
**Analytics pattern detection & feature generation tournaments.**

Miners are evaluated on three pillars:
- **Features**: Schema validation and generation performance (10%)
- **Synthetic Patterns**: Recall of known patterns from ground_truth (30%)
- **Pattern Precision**: Anti-cheat via flow tracing (25%)
- **Novelty Patterns**: Discovery of new valid patterns (25%)
- **Performance**: Detection speed (10%)

All patterns are validated by tracing actual flows in `transfers.parquet`.
        """,
    },
    {
        "name": "Stats",
        "description": """
**Statistics and metrics for tournaments.**

Provides aggregate statistics, miner history, and epoch-level metrics.
Useful for dashboards and performance tracking.
        """,
    },
    {
        "name": "Health",
        "description": "Service health check endpoints.",
    },
]


def custom_openapi():
    """Generate custom OpenAPI schema with enhanced documentation."""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Subnet Analytics Tournaments API",
        version="1.0.0",
        description=(
            "Pattern detection & feature generation evaluation platform for the Bittensor Subnet.\n\n"
            "## Tournament Scoring (Three Pillars)\n\n"
            "Miners are evaluated on **three pillars**:\n\n"
            "### 1. Features (10%)\n"
            "- Output schema validation for `features.parquet`\n"
            "- Generation performance relative to baseline\n\n"
            "### 2. Patterns (55%)\n"
            "- **Synthetic Recall (30%)**: % of ground_truth addresses detected\n"
            "- **Pattern Precision (25%)**: Anti-cheat via flow tracing validation\n\n"
            "### 3. Novelty (25%) + Performance (10%)\n"
            "- **Novelty Discovery (25%)**: New valid patterns beyond ground_truth\n"
            "- **Pattern Performance (10%)**: Detection speed relative to baseline\n\n"
            "## Flow Tracing Validation\n\n"
            "All patterns (synthetic and novelty) are validated by verifying transaction "
            "flows exist in `transfers.parquet`. This prevents gaming through fake patterns.\n\n"
            "## API Versioning\n\n"
            "Current version: `v1`\n\n"
            "All endpoints use `/api/v1/analytics/` prefix.\n\n"
            "## Authentication\n\n"
            "This is a **read-only public API**. No authentication required."
        ),
        routes=app.routes,
        tags=tags_metadata,
    )
    
    # Add server information
    openapi_schema["servers"] = [
        {"url": "/", "description": "Current server"},
    ]
    
    # Add contact and license
    openapi_schema["info"]["contact"] = {
        "name": "Subnet Team",
        "url": "https://github.com/subnet",
    }
    openapi_schema["info"]["license"] = {
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app = FastAPI(
    title="Subnet Analytics Tournaments API",
    description="Pattern detection & feature generation evaluation platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=tags_metadata,
)

# Override with custom OpenAPI schema
app.openapi = custom_openapi

# CORS middleware - read-only API allows all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Include routers
app.include_router(analytics_tournaments_router)
app.include_router(analytics_stats_router)


@app.get(
    "/health",
    tags=["Health"],
    summary="Health Check",
    description="Check if the API service is healthy and responding.",
    response_description="Service health status",
    responses={
        200: {
            "description": "Service is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "service": "analytics-tournament-api",
                        "version": "1.0.0"
                    }
                }
            }
        }
    },
)
async def health_check():
    """
    Health check endpoint.
    
    Returns 200 if the service is running and able to respond to requests.
    Used by load balancers and monitoring systems.
    """
    return {
        "status": "healthy",
        "service": "analytics-tournament-api",
        "version": "1.0.0",
    }


@app.get(
    "/",
    tags=["Health"],
    summary="API Root",
    description="Get API information and available endpoints.",
    include_in_schema=False,
)
async def root():
    """API root - returns basic info and links to documentation."""
    return {
        "name": "Subnet Analytics Tournaments API",
        "version": "1.0.0",
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json",
        },
        "endpoints": {
            "tournaments": "/api/v1/analytics/tournaments",
            "stats": "/api/v1/analytics/stats",
        },
    }
