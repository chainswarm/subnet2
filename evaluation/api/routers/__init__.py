"""
API Routers for the Analytics Tournament Evaluation System.

Current:
- Analytics: /api/v1/analytics/... - Pattern detection & feature generation

Future tournament types:
- ML: /api/v1/ml/... - Machine learning tournaments
- LLM: /api/v1/llm/... - Language model tournaments
"""

from evaluation.api.routers.analytics_tournaments import router as analytics_tournaments_router
from evaluation.api.routers.analytics_stats import router as analytics_stats_router


__all__ = [
    "analytics_tournaments_router",
    "analytics_stats_router",
]
