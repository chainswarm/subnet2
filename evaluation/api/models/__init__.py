"""
Response models for the Analytics Tournament Evaluation API.

All models use the three-pillar scoring system:
- Feature Performance (10%): Schema validation + generation speed
- Synthetic Recall (30%): Detection of ground_truth patterns
- Pattern Precision (25%): Anti-cheat via flow tracing
- Novelty Discovery (25%): New valid patterns beyond ground_truth
- Pattern Performance (10%): Detection speed
"""

from evaluation.api.models.responses import (
    # Tournament models
    TournamentResponse,
    TournamentDetailResponse,
    SubmissionResponse,
    EvaluationRunResponse,
    TournamentResultResponse,
    LeaderboardEntry,
    LeaderboardResponse,
    
    # Stats models
    StatsResponse,
    MinerHistoryResponse,
    EpochStatsResponse,
)


__all__ = [
    # Tournament models
    "TournamentResponse",
    "TournamentDetailResponse",
    "SubmissionResponse",
    "EvaluationRunResponse",
    "TournamentResultResponse",
    "LeaderboardEntry",
    "LeaderboardResponse",
    
    # Stats models
    "StatsResponse",
    "MinerHistoryResponse",
    "EpochStatsResponse",
]
