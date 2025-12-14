from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class TournamentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    name: str
    netuid: int
    status: str
    registration_start: datetime
    registration_end: datetime
    start_block: int
    end_block: int
    epoch_blocks: int
    test_networks: list[str]
    baseline_repository: Optional[str]
    baseline_version: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
    submission_count: int


class TournamentDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    name: str
    netuid: int
    status: str
    registration_start: datetime
    registration_end: datetime
    start_block: int
    end_block: int
    epoch_blocks: int
    test_networks: list[str]
    baseline_repository: Optional[str]
    baseline_version: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
    submissions: list["SubmissionResponse"]
    results: list["TournamentResultResponse"]


class SubmissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    tournament_id: str
    hotkey: str
    uid: int
    repository_url: str
    commit_hash: str
    docker_image_tag: Optional[str]
    status: str
    validation_error: Optional[str]
    submitted_at: datetime
    validated_at: Optional[datetime]
    run_count: int


class EvaluationRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    submission_id: str
    hotkey: str
    epoch_number: int
    network: str
    test_date: date
    status: str
    execution_time_seconds: Optional[float]
    exit_code: Optional[int]
    pattern_recall: Optional[float]
    data_correctness: Optional[bool]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]


class TournamentResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    tournament_id: str
    hotkey: str
    uid: int
    pattern_accuracy_score: float
    data_correctness_score: float
    performance_score: float
    final_score: float
    rank: int
    beat_baseline: bool
    is_winner: bool
    calculated_at: datetime


class MinerTournamentEntry(BaseModel):
    tournament_id: str
    tournament_name: str
    status: str
    rank: Optional[int]
    final_score: Optional[float]
    beat_baseline: bool
    is_winner: bool
    submitted_at: datetime


class MinerHistoryResponse(BaseModel):
    hotkey: str
    total_tournaments: int
    total_wins: int
    total_baseline_beats: int
    average_rank: Optional[float]
    best_rank: Optional[int]
    tournaments: list[MinerTournamentEntry]


class StatsResponse(BaseModel):
    active_tournaments: int
    completed_tournaments: int
    total_miners: int
    total_submissions: int
    total_runs_completed: int
    average_pattern_recall: Optional[float]
    baseline_beat_rate: Optional[float]
