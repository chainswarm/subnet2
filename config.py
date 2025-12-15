from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "subnet2"
    postgres_user: str = "subnet2"
    postgres_password: str

    redis_url: str = "redis://localhost:6379/0"

    repos_path: str = "/tmp/evaluation/repos"
    data_path: str = "/tmp/evaluation/data"

    benchmark_max_execution_time: int = 3600
    benchmark_memory_limit: str = "32g"

    evaluation_build_timeout_seconds: int = 600
    evaluation_run_timeout_seconds: int = 300
    evaluation_memory_limit_mb: int = 8192
    evaluation_cpu_limit: float = 2.0

    wallet_name: str = "default"
    wallet_hotkey: str = "default"
    subtensor_network: str = "finney"
    submission_timeout_seconds: int = 30

    # Tournament Timing Configuration
    tournament_submission_duration_seconds: int = 120
    tournament_epoch_count: int = 3
    tournament_epoch_duration_seconds: int = 180
    tournament_networks: str = "torus"
    tournament_schedule_mode: str = "manual"  # "manual" or "daily"

    class Config:
        env_prefix = ""
        env_file = ".env"
        extra = "ignore"

    def get_database_url(self) -> str:
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def tournament_networks_list(self) -> List[str]:
        """Parse comma-separated networks into list"""
        return [n.strip() for n in self.tournament_networks.split(",")]


config = Settings()
