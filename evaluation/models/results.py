from dataclasses import dataclass
from typing import Optional


@dataclass
class ContainerResult:
    exit_code: int
    execution_time_seconds: float
    timed_out: bool
    logs: str


@dataclass
class ScoreResult:
    pattern_recall: float
    data_correctness: bool
    execution_time: float
    final_score: float


@dataclass
class SubmissionResult:
    success: bool
    docker_image_tag: Optional[str] = None
    error_message: Optional[str] = None
