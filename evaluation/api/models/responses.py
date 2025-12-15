"""
Pydantic response models for the Analytics Tournament Evaluation API.

These models define the JSON response structures for all API endpoints,
with rich documentation for OpenAPI schema generation.

Scoring Model (Three Pillars):
- Feature Performance (10%): Schema validation + generation speed
- Synthetic Recall (30%): Detection of ground_truth patterns
- Pattern Precision (25%): Anti-cheat via flow tracing
- Novelty Discovery (25%): New valid patterns beyond ground_truth
- Pattern Performance (10%): Detection speed
"""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# TOURNAMENT RESPONSE MODELS
# =============================================================================

class TournamentResponse(BaseModel):
    """
    Summary information for an Analytics tournament.
    
    Analytics tournaments evaluate miners on pattern detection and feature
    generation using synthetic blockchain data.
    """
    
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(
        ...,
        description="Unique tournament identifier (UUID)",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    epoch_number: int = Field(
        ...,
        description="Epoch number for this tournament",
        examples=[8],
        ge=1,
    )
    status: str = Field(
        ...,
        description="Current status: pending, in_progress, evaluating, completed, or failed",
        examples=["completed"],
    )
    started_at: Optional[datetime] = Field(
        None,
        description="When evaluation started (ISO 8601 timestamp)",
        examples=["2025-01-09T00:00:00Z"],
    )
    completed_at: Optional[datetime] = Field(
        None,
        description="When evaluation completed (null if not completed)",
        examples=["2025-01-09T23:59:59Z"],
    )
    total_submissions: int = Field(
        ...,
        description="Total number of miner submissions",
        examples=[45],
        ge=0,
    )
    total_evaluation_runs: int = Field(
        ...,
        description="Total evaluation runs executed",
        examples=[180],
        ge=0,
    )
    test_networks: list[str] = Field(
        ...,
        description="Networks used for evaluation",
        examples=[["torus", "mainnet"]],
    )
    baseline_repository: Optional[str] = Field(
        None,
        description="Git repository URL for the baseline implementation",
        examples=["https://github.com/subnet/baseline"],
    )
    baseline_version: Optional[str] = Field(
        None,
        description="Version tag of the baseline implementation",
        examples=["v2.1.0"],
    )
    created_at: datetime = Field(
        ...,
        description="When the tournament was created (ISO 8601 timestamp)",
        examples=["2025-01-09T00:00:00Z"],
    )


class SubmissionResponse(BaseModel):
    """
    Miner submission for a tournament.
    """
    
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(
        ...,
        description="Unique submission identifier (UUID)",
        examples=["7c9e6679-7425-40de-944b-e07fc1f90ae7"],
    )
    tournament_id: str = Field(
        ...,
        description="Tournament this submission belongs to (UUID)",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    hotkey: str = Field(
        ...,
        description="Miner's Bittensor hotkey (SS58 address)",
        examples=["5FA3bxMN3a8XekbmQ2VwwmKv8YLHyv9dRn5uGVpVUPTJDxNQ"],
    )
    uid: int = Field(
        ...,
        description="Miner's UID on the subnet",
        examples=[42],
        ge=0,
    )
    docker_image_digest: str = Field(
        ...,
        description="Docker image digest for reproducible evaluation",
        examples=["sha256:a1b2c3d4e5f6..."],
    )
    status: str = Field(
        ...,
        description="Submission status: pending, validating, valid, or invalid",
        examples=["valid"],
    )
    validation_error: Optional[str] = Field(
        None,
        description="Error message if validation failed",
        examples=["Dockerfile missing required HEALTHCHECK instruction"],
    )
    submitted_at: datetime = Field(
        ...,
        description="When the submission was received (ISO 8601 timestamp)",
        examples=["2025-01-09T10:30:00Z"],
    )
    validated_at: Optional[datetime] = Field(
        None,
        description="When validation completed (null if pending)",
        examples=["2025-01-09T10:35:00Z"],
    )


class EvaluationRunResponse(BaseModel):
    """
    Evaluation run for a tournament.
    
    Contains detailed scoring breakdown with the three-pillar model:
    - Features: Schema validation and generation performance
    - Synthetic Patterns: Recall of known patterns from ground_truth
    - Novelty Patterns: Discovery of new valid patterns via flow tracing
    """
    
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(
        ...,
        description="Unique run identifier (UUID)",
        examples=["e47ac10b-58cc-4372-a567-0e02b2c3d479"],
    )
    submission_id: str = Field(
        ...,
        description="Submission being evaluated (UUID)",
        examples=["7c9e6679-7425-40de-944b-e07fc1f90ae7"],
    )
    hotkey: str = Field(
        ...,
        description="Miner's Bittensor hotkey",
        examples=["5FA3bxMN3a8XekbmQ2VwwmKv8YLHyv9dRn5uGVpVUPTJDxNQ"],
    )
    epoch_number: int = Field(
        ...,
        description="Epoch number within the tournament",
        examples=[8],
        ge=1,
    )
    network: str = Field(
        ...,
        description="Network used for this evaluation run",
        examples=["torus"],
    )
    test_date: date = Field(
        ...,
        description="Date of the test data used (ISO 8601 date)",
        examples=["2025-01-09"],
    )
    status: str = Field(
        ...,
        description="Run status: pending, running, completed, failed, or timeout",
        examples=["completed"],
    )
    
    # Gate 1: Output Schema Validation
    output_schema_valid: Optional[bool] = Field(
        None,
        description="Whether output files passed schema validation",
        examples=[True],
    )
    feature_generation_time_seconds: Optional[float] = Field(
        None,
        description="Time to generate features.parquet (seconds)",
        examples=[12.3],
        ge=0,
    )
    
    # Gate 2: Pattern Validation
    pattern_existence: Optional[bool] = Field(
        None,
        description="Whether at least one valid pattern was detected",
        examples=[True],
    )
    patterns_reported: Optional[int] = Field(
        None,
        description="Total patterns reported by miner",
        examples=[180],
        ge=0,
    )
    
    # Synthetic Patterns (from ground_truth)
    synthetic_addresses_expected: Optional[int] = Field(
        None,
        description="Total addresses in ground_truth to detect",
        examples=[3862],
        ge=0,
    )
    synthetic_addresses_found: Optional[int] = Field(
        None,
        description="Ground truth addresses correctly detected by miner",
        examples=[3650],
        ge=0,
    )
    
    # Novelty Patterns (miner discoveries)
    novelty_patterns_valid: Optional[int] = Field(
        None,
        description="Novel patterns verified via flow tracing",
        examples=[25],
        ge=0,
    )
    novelty_patterns_invalid: Optional[int] = Field(
        None,
        description="Invalid patterns (flows don't exist in transfers.parquet)",
        examples=[13],
        ge=0,
    )
    
    pattern_detection_time_seconds: Optional[float] = Field(
        None,
        description="Time to detect patterns (seconds)",
        examples=[45.2],
        ge=0,
    )
    
    # Component Scores (0.0 to 1.0)
    feature_performance_score: Optional[float] = Field(
        None,
        description="Feature generation performance score (10% weight)",
        examples=[0.549],
        ge=0.0,
        le=1.0,
    )
    synthetic_recall_score: Optional[float] = Field(
        None,
        description="Synthetic pattern recall score (30% weight)",
        examples=[0.947],
        ge=0.0,
        le=1.0,
    )
    pattern_precision_score: Optional[float] = Field(
        None,
        description="Pattern precision score - anti-cheat (25% weight)",
        examples=[0.928],
        ge=0.0,
        le=1.0,
    )
    novelty_discovery_score: Optional[float] = Field(
        None,
        description="Novelty pattern discovery score (25% weight)",
        examples=[0.333],
        ge=0.0,
        le=1.0,
    )
    pattern_performance_score: Optional[float] = Field(
        None,
        description="Pattern detection performance score (10% weight)",
        examples=[0.525],
        ge=0.0,
        le=1.0,
    )
    
    # Final Score
    final_score: Optional[float] = Field(
        None,
        description="Weighted final score combining all components",
        examples=[0.707],
        ge=0.0,
        le=1.0,
    )
    
    # Execution Metadata
    exit_code: Optional[int] = Field(
        None,
        description="Container exit code (0 = success)",
        examples=[0],
    )
    started_at: Optional[datetime] = Field(
        None,
        description="When execution started (ISO 8601 timestamp)",
        examples=["2025-01-09T10:00:00Z"],
    )
    completed_at: Optional[datetime] = Field(
        None,
        description="When execution completed (ISO 8601 timestamp)",
        examples=["2025-01-09T10:01:00Z"],
    )
    error_message: Optional[str] = Field(
        None,
        description="Error message if the run failed",
        examples=["Container exceeded memory limit"],
    )


class TournamentResultResponse(BaseModel):
    """
    Tournament result for a single miner.
    
    Contains aggregated scores across all evaluation runs and final ranking.
    """
    
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(
        ...,
        description="Unique result identifier (UUID)",
        examples=["f47ac10b-58cc-4372-a567-0e02b2c3d470"],
    )
    tournament_id: str = Field(
        ...,
        description="Tournament this result belongs to (UUID)",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    hotkey: str = Field(
        ...,
        description="Miner's Bittensor hotkey",
        examples=["5FA3bxMN3a8XekbmQ2VwwmKv8YLHyv9dRn5uGVpVUPTJDxNQ"],
    )
    uid: int = Field(
        ...,
        description="Miner's UID on the subnet",
        examples=[42],
        ge=0,
    )
    
    # Gate Pass Rates
    output_schema_validity_rate: Optional[float] = Field(
        None,
        description="Percentage of runs with valid output schema (0.0 to 1.0)",
        examples=[1.0],
        ge=0.0,
        le=1.0,
    )
    pattern_existence_rate: Optional[float] = Field(
        None,
        description="Percentage of runs with at least one valid pattern (0.0 to 1.0)",
        examples=[1.0],
        ge=0.0,
        le=1.0,
    )
    
    # Aggregated Component Scores (means across all runs)
    feature_performance_score: Optional[float] = Field(
        None,
        description="Mean feature generation performance (10% weight)",
        examples=[0.549],
        ge=0.0,
        le=1.0,
    )
    synthetic_recall_score: Optional[float] = Field(
        None,
        description="Mean synthetic pattern recall (30% weight)",
        examples=[0.947],
        ge=0.0,
        le=1.0,
    )
    pattern_precision_score: Optional[float] = Field(
        None,
        description="Mean pattern precision (25% weight)",
        examples=[0.928],
        ge=0.0,
        le=1.0,
    )
    novelty_discovery_score: Optional[float] = Field(
        None,
        description="Mean novelty discovery score (25% weight)",
        examples=[0.333],
        ge=0.0,
        le=1.0,
    )
    pattern_performance_score: Optional[float] = Field(
        None,
        description="Mean pattern detection performance (10% weight)",
        examples=[0.525],
        ge=0.0,
        le=1.0,
    )
    
    # Totals across all runs
    total_runs: Optional[int] = Field(
        None,
        description="Total evaluation runs for this miner",
        examples=[4],
        ge=0,
    )
    total_patterns_reported: Optional[int] = Field(
        None,
        description="Total patterns reported across all runs",
        examples=[720],
        ge=0,
    )
    total_synthetic_found: Optional[int] = Field(
        None,
        description="Total ground truth addresses found",
        examples=[14600],
        ge=0,
    )
    total_novelty_valid: Optional[int] = Field(
        None,
        description="Total valid novelty patterns discovered",
        examples=[100],
        ge=0,
    )
    total_novelty_invalid: Optional[int] = Field(
        None,
        description="Total invalid pattern claims",
        examples=[52],
        ge=0,
    )
    
    # Final Score and Ranking
    final_score: float = Field(
        ...,
        description="Weighted final score combining all components",
        examples=[0.707],
        ge=0.0,
        le=1.0,
    )
    rank: int = Field(
        ...,
        description="Final ranking position (1 = first place)",
        examples=[1],
        ge=1,
    )
    beat_baseline: bool = Field(
        ...,
        description="Whether the miner's score exceeded the baseline",
        examples=[True],
    )
    is_winner: bool = Field(
        ...,
        description="Whether this miner won the tournament",
        examples=[True],
    )
    calculated_at: datetime = Field(
        ...,
        description="When the final score was calculated (ISO 8601 timestamp)",
        examples=["2025-01-20T12:00:00Z"],
    )


class TournamentDetailResponse(BaseModel):
    """
    Complete tournament information including submissions and results.
    """
    
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(
        ...,
        description="Unique tournament identifier (UUID)",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    epoch_number: int = Field(
        ...,
        description="Epoch number for this tournament",
        examples=[8],
    )
    status: str = Field(
        ...,
        description="Current status",
        examples=["completed"],
    )
    started_at: Optional[datetime] = Field(
        None,
        description="When evaluation started",
    )
    completed_at: Optional[datetime] = Field(
        None,
        description="When evaluation completed",
    )
    total_submissions: int = Field(
        ...,
        description="Total number of submissions",
    )
    total_evaluation_runs: int = Field(
        ...,
        description="Total evaluation runs",
    )
    test_networks: list[str] = Field(
        ...,
        description="Networks used for evaluation",
    )
    baseline_repository: Optional[str] = Field(
        None,
        description="Baseline repository URL",
    )
    baseline_version: Optional[str] = Field(
        None,
        description="Baseline version",
    )
    created_at: datetime = Field(
        ...,
        description="When the tournament was created",
    )
    submissions: list[SubmissionResponse] = Field(
        ...,
        description="All submissions in this tournament",
    )
    results: list[TournamentResultResponse] = Field(
        ...,
        description="Final results sorted by rank (empty if not completed)",
    )


class LeaderboardEntry(BaseModel):
    """
    Single entry in the tournament leaderboard.
    """
    
    rank: int = Field(
        ...,
        description="Current ranking position",
        examples=[1],
        ge=1,
    )
    hotkey: str = Field(
        ...,
        description="Miner's Bittensor hotkey",
        examples=["5FA3bxMN3a8XekbmQ2VwwmKv8YLHyv9dRn5uGVpVUPTJDxNQ"],
    )
    uid: int = Field(
        ...,
        description="Miner's UID",
        examples=[42],
        ge=0,
    )
    final_score: float = Field(
        ...,
        description="Final weighted score",
        examples=[0.707],
        ge=0.0,
        le=1.0,
    )
    synthetic_recall_score: Optional[float] = Field(
        None,
        description="Synthetic pattern recall",
        examples=[0.947],
    )
    pattern_precision_score: Optional[float] = Field(
        None,
        description="Pattern precision",
        examples=[0.928],
    )
    novelty_discovery_score: Optional[float] = Field(
        None,
        description="Novelty discovery score",
        examples=[0.333],
    )
    beat_baseline: bool = Field(
        ...,
        description="Whether the miner beat baseline",
        examples=[True],
    )


class LeaderboardResponse(BaseModel):
    """
    Full leaderboard for a tournament.
    """
    
    tournament_id: str = Field(
        ...,
        description="Tournament identifier",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    epoch_number: int = Field(
        ...,
        description="Epoch number",
        examples=[8],
    )
    status: str = Field(
        ...,
        description="Tournament status",
        examples=["completed"],
    )
    entries: list[LeaderboardEntry] = Field(
        ...,
        description="Leaderboard entries sorted by rank",
    )
    total_participants: int = Field(
        ...,
        description="Total miners participating",
        examples=[45],
    )
    baseline_beat_count: int = Field(
        ...,
        description="Number of miners who beat baseline",
        examples=[38],
    )


# =============================================================================
# STATS RESPONSE MODELS
# =============================================================================

class MinerHistoryResponse(BaseModel):
    """
    Complete history and statistics for a miner across all tournaments.
    """
    
    hotkey: str = Field(
        ...,
        description="Miner's Bittensor hotkey",
        examples=["5FA3bxMN3a8XekbmQ2VwwmKv8YLHyv9dRn5uGVpVUPTJDxNQ"],
    )
    total_tournaments: int = Field(
        ...,
        description="Total tournaments participated in",
        examples=[7],
        ge=0,
    )
    total_wins: int = Field(
        ...,
        description="Number of tournaments won",
        examples=[4],
        ge=0,
    )
    total_baseline_beats: int = Field(
        ...,
        description="Times the miner beat baseline",
        examples=[6],
        ge=0,
    )
    average_final_score: Optional[float] = Field(
        None,
        description="Average final score",
        examples=[0.72],
    )
    average_rank: Optional[float] = Field(
        None,
        description="Average ranking position",
        examples=[2.3],
    )
    best_rank: Optional[int] = Field(
        None,
        description="Best ranking achieved",
        examples=[1],
    )
    
    # Score component averages
    avg_synthetic_recall: Optional[float] = Field(
        None,
        description="Average synthetic recall score",
        examples=[0.92],
    )
    avg_pattern_precision: Optional[float] = Field(
        None,
        description="Average pattern precision",
        examples=[0.88],
    )
    avg_novelty_discovery: Optional[float] = Field(
        None,
        description="Average novelty discovery score",
        examples=[0.35],
    )
    
    # Total discoveries
    total_novelty_patterns_found: Optional[int] = Field(
        None,
        description="Total novel patterns discovered across all tournaments",
        examples=[234],
    )
    
    recent_results: list[TournamentResultResponse] = Field(
        ...,
        description="Recent tournament results, most recent first",
    )


class StatsResponse(BaseModel):
    """
    Aggregate statistics for tournaments.
    """
    
    active_tournaments: int = Field(
        ...,
        description="Tournaments currently in progress",
        examples=[1],
        ge=0,
    )
    completed_tournaments: int = Field(
        ...,
        description="Completed tournaments",
        examples=[12],
        ge=0,
    )
    total_miners: int = Field(
        ...,
        description="Unique miners who have participated",
        examples=[127],
        ge=0,
    )
    total_submissions: int = Field(
        ...,
        description="Total submissions across all tournaments",
        examples=[452],
        ge=0,
    )
    total_runs_completed: int = Field(
        ...,
        description="Total evaluation runs completed",
        examples=[2451],
        ge=0,
    )
    
    # Score averages
    avg_synthetic_recall: Optional[float] = Field(
        None,
        description="Average synthetic recall across all runs",
        examples=[0.847],
        ge=0.0,
        le=1.0,
    )
    avg_pattern_precision: Optional[float] = Field(
        None,
        description="Average pattern precision",
        examples=[0.912],
        ge=0.0,
        le=1.0,
    )
    avg_novelty_discovery: Optional[float] = Field(
        None,
        description="Average novelty discovery score",
        examples=[0.287],
        ge=0.0,
        le=1.0,
    )
    
    # Novelty totals
    total_novelty_patterns_found: Optional[int] = Field(
        None,
        description="Total novel patterns discovered by all miners",
        examples=[12847],
    )
    
    baseline_beat_rate: Optional[float] = Field(
        None,
        description="Proportion of miners who beat baseline",
        examples=[0.673],
        ge=0.0,
        le=1.0,
    )


class EpochStatsResponse(BaseModel):
    """
    Statistics for a specific epoch's tournament.
    """
    
    epoch_number: int = Field(
        ...,
        description="Epoch number",
        examples=[8],
    )
    tournament_id: Optional[str] = Field(
        None,
        description="Tournament identifier",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    status: str = Field(
        ...,
        description="Tournament status",
        examples=["completed"],
    )
    total_participants: int = Field(
        ...,
        description="Number of miners who participated",
        examples=[45],
        ge=0,
    )
    total_runs: int = Field(
        ...,
        description="Total evaluation runs",
        examples=[180],
        ge=0,
    )
    
    # Score statistics
    avg_final_score: Optional[float] = Field(
        None,
        description="Average final score",
        examples=[0.65],
    )
    top_score: Optional[float] = Field(
        None,
        description="Highest score achieved",
        examples=[0.92],
    )
    avg_synthetic_recall: Optional[float] = Field(
        None,
        description="Average synthetic recall",
        examples=[0.85],
    )
    avg_pattern_precision: Optional[float] = Field(
        None,
        description="Average pattern precision",
        examples=[0.91],
    )
    avg_novelty_discovery: Optional[float] = Field(
        None,
        description="Average novelty discovery",
        examples=[0.30],
    )
    
    # Winner info
    winner_hotkey: Optional[str] = Field(
        None,
        description="Winner's hotkey",
        examples=["5FA3bxMN3a8XekbmQ2VwwmKv8YLHyv9dRn5uGVpVUPTJDxNQ"],
    )
    winner_score: Optional[float] = Field(
        None,
        description="Winner's final score",
        examples=[0.92],
    )
    
    # Novelty discoveries
    total_novelty_found: Optional[int] = Field(
        None,
        description="Total novel patterns found in this epoch",
        examples=[287],
    )
    
    baseline_beat_count: int = Field(
        ...,
        description="Number of miners who beat baseline",
        examples=[38],
        ge=0,
    )
