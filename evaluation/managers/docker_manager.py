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
    def __init__(self, tournament_id: UUID, epoch_number: int, hotkey: str, data_dir: Optional[Path] = None):
        """
        Initialize DockerManager with hierarchical directory structure.
        
        Args:
            tournament_id: Tournament UUID
            epoch_number: Epoch number (0-based)
            hotkey: Miner hotkey for organizing outputs
            data_dir: Optional base data directory (defaults to temp/subnet/analytics)
        """
        self.tournament_id = tournament_id
        self.epoch_number = epoch_number
        self.hotkey = hotkey
        
        # Build hierarchical base path: {temp_dir}/subnet/analytics/
        base_dir = data_dir or Path(tempfile.gettempdir()) / "subnet" / "analytics"
        
        # Full hierarchical path: tournaments/{tournament_id}/epochs/{epoch_number}/
        self.data_dir = (
            base_dir / "tournaments" / str(tournament_id) / "epochs" / str(epoch_number)
        )
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def prepare_input_data(self, transfers_df: pd.DataFrame) -> tuple[Path, Path]:
        """
        Prepare input data in hierarchical structure.
        
        Input is SHARED at epoch level (all miners use same data):
          {data_dir}/input/transfers.parquet
        
        Output is PER-HOTKEY:
          {data_dir}/output/{hotkey}/
        
        Returns:
            Tuple of (input_dir, output_dir) paths
        """
        # Shared input directory at epoch level
        input_dir = self.data_dir / "input"
        input_dir.mkdir(parents=True, exist_ok=True)

        transfers_path = input_dir / "transfers.parquet"
        
        # Only write if it doesn't exist (shared across all miners in this epoch)
        if not transfers_path.exists():
            transfers_df.to_parquet(transfers_path, index=False)
            logger.debug(
                "input_prepared",
                tournament_id=str(self.tournament_id),
                epoch_number=self.epoch_number,
                rows=len(transfers_df)
            )
        else:
            logger.debug(
                "input_reused",
                tournament_id=str(self.tournament_id),
                epoch_number=self.epoch_number,
                hotkey=self.hotkey
            )
        
        # Per-hotkey output directory
        output_dir = self.data_dir / "output" / self.hotkey
        output_dir.mkdir(parents=True, exist_ok=True)
        
        return input_dir, output_dir

    def run_container(
        self,
        image_tag: str,
        run_id: UUID,
        transfers_df: pd.DataFrame,
    ) -> ContainerResult:
        # Prepare shared input and per-hotkey output directories
        input_dir, output_dir = self.prepare_input_data(transfers_df)

        container_name = f"subnet2-run-{run_id}"

        cmd = [
            "docker", "run",
            "--name", container_name,
            "--network", "none",
            "--memory", f"{config.evaluation_memory_limit_mb}m",
            "--cpus", str(config.evaluation_cpu_limit),
            "--read-only",
            "--tmpfs", "/tmp:size=100m",
            "-v", f"{input_dir}:/data/input:ro",  # Shared epoch-level input
            "-v", f"{output_dir}:/data/output:rw",  # Per-hotkey output
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
            logger.warning("container_timeout", run_id=str(run_id), hotkey=self.hotkey)
            return ContainerResult(
                exit_code=-1,
                execution_time_seconds=execution_time,
                timed_out=True,
                logs="",
            )
        finally:
            subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)

    def read_features(self) -> Optional[pd.DataFrame]:
        """
        Read features.parquet output from miner container.
        
        Path: {data_dir}/output/{hotkey}/features.parquet
            
        Returns:
            DataFrame with features or None if not found
        """
        features_path = self.data_dir / "output" / self.hotkey / "features.parquet"
        
        if not features_path.exists():
            logger.warning("features_not_found", hotkey=self.hotkey)
            return None
        
        try:
            df = pd.read_parquet(features_path)
            logger.debug("features_loaded", hotkey=self.hotkey, rows=len(df))
            return df
        except Exception as e:
            logger.error("features_read_error", hotkey=self.hotkey, error=str(e))
            return None

    def read_patterns(self) -> Optional[pd.DataFrame]:
        """
        Read patterns output from miner container.
        
        Path: {data_dir}/output/{hotkey}/patterns.parquet (or patterns_*.parquet)
        
        Handles both:
        - Single patterns.parquet file
        - Multiple patterns_*.parquet files (merged)
            
        Returns:
            DataFrame with patterns or None if not found
        """
        output_dir = self.data_dir / "output" / self.hotkey
        patterns_path = output_dir / "patterns.parquet"
        
        # Try single patterns.parquet first
        if patterns_path.exists():
            try:
                df = pd.read_parquet(patterns_path)
                logger.debug("patterns_loaded", hotkey=self.hotkey, rows=len(df))
                return df
            except Exception as e:
                logger.error("patterns_read_error", hotkey=self.hotkey, error=str(e))
                return None
        
        # Try multiple patterns_*.parquet files
        pattern_files = list(output_dir.glob("patterns_*.parquet"))
        
        if pattern_files:
            try:
                dfs = [pd.read_parquet(f) for f in pattern_files]
                merged = pd.concat(dfs, ignore_index=True)
                logger.debug("patterns_merged", hotkey=self.hotkey, files=len(pattern_files), rows=len(merged))
                return merged
            except Exception as e:
                logger.error("patterns_merge_error", hotkey=self.hotkey, error=str(e))
                return None
        
        logger.warning("no_patterns_output", hotkey=self.hotkey)
        return None

    def cleanup_hotkey(self) -> None:
        """
        Clean up hotkey output directory after evaluation.
        
        Path: {data_dir}/output/{hotkey}/
        """
        hotkey_dir = self.data_dir / "output" / self.hotkey
        if hotkey_dir.exists():
            shutil.rmtree(hotkey_dir)
            logger.debug("hotkey_output_cleaned", hotkey=self.hotkey)
