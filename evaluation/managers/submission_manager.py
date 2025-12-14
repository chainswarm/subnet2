import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
from uuid import UUID

from loguru import logger

from config import config
from evaluation.models.results import SubmissionResult
from evaluation.security import CodeScanner, DockerfileValidator, FileValidator


class SubmissionManager:
    def __init__(self, work_dir: Optional[Path] = None):
        self.work_dir = work_dir or Path(tempfile.gettempdir()) / "subnet2_submissions"
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def clone_repository(self, repository_url: str, commit_hash: str, submission_id: UUID) -> Path:
        clone_path = self.work_dir / str(submission_id)
        if clone_path.exists():
            shutil.rmtree(clone_path)

        result = subprocess.run(
            ["git", "clone", "--depth", "1", repository_url, str(clone_path)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            raise ValueError(f"clone_failed: {result.stderr}")

        checkout_result = subprocess.run(
            ["git", "checkout", commit_hash],
            cwd=clone_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if checkout_result.returncode != 0:
            raise ValueError(f"checkout_failed: {checkout_result.stderr}")

        logger.info("repository_cloned", submission_id=str(submission_id), commit=commit_hash)
        return clone_path

    def validate_dockerfile(self, repo_path: Path) -> bool:
        dockerfile = repo_path / "Dockerfile"
        if not dockerfile.exists():
            raise ValueError("dockerfile_not_found")

        dockerfile_validator = DockerfileValidator()
        if not dockerfile_validator.is_valid(dockerfile):
            violations = dockerfile_validator.validate(dockerfile)
            raise ValueError(f"dockerfile_validation_failed: {violations[0]['message']}")

        return True

    def validate_submission(self, repo_path: Path) -> None:
        file_validator = FileValidator()
        if not file_validator.is_valid(repo_path):
            violations = file_validator.validate_directory(repo_path)
            raise ValueError(f"file_validation_failed: {violations[0]['message']}")

        code_scanner = CodeScanner()
        if not code_scanner.is_safe(repo_path):
            violations = code_scanner.scan_directory(repo_path)
            raise ValueError(f"code_scan_failed: {violations[0]['message']}")

        dockerfile = repo_path / "Dockerfile"
        dockerfile_validator = DockerfileValidator()
        if not dockerfile_validator.is_valid(dockerfile):
            violations = dockerfile_validator.validate(dockerfile)
            raise ValueError(f"dockerfile_validation_failed: {violations[0]['message']}")

        logger.info("submission_validated", repo_path=str(repo_path))

    def build_image(self, repo_path: Path, submission_id: UUID) -> str:
        image_tag = f"subnet2-analyzer:{submission_id}"

        result = subprocess.run(
            ["docker", "build", "-t", image_tag, "."],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=config.evaluation_build_timeout_seconds,
        )
        if result.returncode != 0:
            raise ValueError(f"build_failed: {result.stderr}")

        logger.info("image_built", submission_id=str(submission_id), tag=image_tag)
        return image_tag

    def process_submission(
        self,
        repository_url: str,
        commit_hash: str,
        submission_id: UUID,
    ) -> SubmissionResult:
        try:
            repo_path = self.clone_repository(repository_url, commit_hash, submission_id)
            self.validate_dockerfile(repo_path)
            image_tag = self.build_image(repo_path, submission_id)
            return SubmissionResult(success=True, docker_image_tag=image_tag)
        except ValueError as e:
            logger.warning("submission_failed", submission_id=str(submission_id), error=str(e))
            return SubmissionResult(success=False, error_message=str(e))
        except subprocess.TimeoutExpired:
            logger.warning("submission_timeout", submission_id=str(submission_id))
            return SubmissionResult(success=False, error_message="timeout")

    def cleanup(self, submission_id: UUID) -> None:
        repo_path = self.work_dir / str(submission_id)
        if repo_path.exists():
            shutil.rmtree(repo_path)

        image_tag = f"subnet2-analyzer:{submission_id}"
        subprocess.run(["docker", "rmi", "-f", image_tag], capture_output=True)
