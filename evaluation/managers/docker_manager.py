import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional
from uuid import UUID

import pandas as pd
from loguru import logger

from evaluation.models.results import ContainerResult
from config import config


class DockerManager:
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path(tempfile.gettempdir()) / "subnet2_data"
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def prepare_input_data(self, run_id: UUID, transfers_df: pd.DataFrame) -> Path:
        run_dir = self.data_dir / str(run_id)
        input_dir = run_dir / "input"
        input_dir.mkdir(parents=True, exist_ok=True)

        transfers_path = input_dir / "transfers.parquet"
        transfers_df.to_parquet(transfers_path, index=False)

        logger.debug("input_prepared", run_id=str(run_id), rows=len(transfers_df))
        return run_dir

    def run_container(
        self,
        image_tag: str,
        run_id: UUID,
        transfers_df: pd.DataFrame,
    ) -> ContainerResult:
        run_dir = self.prepare_input_data(run_id, transfers_df)
        output_dir = run_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        container_name = f"subnet2-run-{run_id}"

        cmd = [
            "docker", "run",
            "--name", container_name,
            "--network", "none",
            "--memory", f"{config.evaluation_memory_limit_mb}m",
            "--cpus", str(config.evaluation_cpu_limit),
            "--read-only",
            "--tmpfs", "/tmp:size=100m",
            "-v", f"{run_dir / 'input'}:/data/input:ro",
            "-v", f"{output_dir}:/data/output:rw",
            image_tag,
        ]

        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=config.evaluation_run_timeout_seconds,
            )
            execution_time = time.time() - start_time

            logs = result.stdout + result.stderr

            return ContainerResult(
                exit_code=result.returncode,
                execution_time_seconds=execution_time,
                timed_out=False,
                logs=logs[:10000],
            )
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            subprocess.run(["docker", "kill", container_name], capture_output=True)
            logger.warning("container_timeout", run_id=str(run_id))
            return ContainerResult(
                exit_code=-1,
                execution_time_seconds=execution_time,
                timed_out=True,
                logs="",
            )
        finally:
            subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)

    def read_output(self, run_id: UUID) -> Optional[pd.DataFrame]:
        output_path = self.data_dir / str(run_id) / "output" / "patterns.parquet"
        if not output_path.exists():
            return None
        try:
            return pd.read_parquet(output_path)
        except Exception as e:
            logger.warning("output_read_failed", run_id=str(run_id), error=str(e))
            return None

    def cleanup_run(self, run_id: UUID) -> None:
        run_dir = self.data_dir / str(run_id)
        if run_dir.exists():
            shutil.rmtree(run_dir)
