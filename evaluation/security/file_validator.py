from pathlib import Path
from typing import List, Set

from loguru import logger


class FileValidator:
    ALLOWED_EXTENSIONS: Set[str] = {
        ".py",
        ".txt",
        ".md",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".cfg",
        ".ini",
        ".sh",
        ".dockerfile",
        ".gitignore",
        ".dockerignore",
        ".parquet",
        ".csv",
    }

    REQUIRED_FILES: Set[str] = {
        "Dockerfile",
    }

    MAX_FILE_SIZE_MB: float = 10.0
    MAX_TOTAL_SIZE_MB: float = 100.0
    MAX_FILES: int = 500

    def __init__(self):
        self.violations: List[dict] = []

    def validate_directory(self, directory: Path) -> List[dict]:
        self.violations = []

        if not directory.exists():
            raise ValueError(f"directory_not_found: {directory}")

        self._check_required_files(directory)

        all_files = list(directory.rglob("*"))
        files = [f for f in all_files if f.is_file()]

        if len(files) > self.MAX_FILES:
            self.violations.append({
                "type": "too_many_files",
                "message": f"Found {len(files)} files, max is {self.MAX_FILES}",
            })

        total_size = 0
        for file_path in files:
            if file_path.name.startswith("."):
                continue

            self._validate_file(file_path)
            total_size += file_path.stat().st_size

        total_size_mb = total_size / (1024 * 1024)
        if total_size_mb > self.MAX_TOTAL_SIZE_MB:
            self.violations.append({
                "type": "total_size_exceeded",
                "message": f"Total size {total_size_mb:.2f}MB exceeds {self.MAX_TOTAL_SIZE_MB}MB",
            })

        logger.info(
            "file_validation_complete",
            directory=str(directory),
            files_checked=len(files),
            total_size_mb=total_size_mb,
            violations_found=len(self.violations),
        )

        return self.violations

    def _check_required_files(self, directory: Path) -> None:
        for required in self.REQUIRED_FILES:
            if not (directory / required).exists():
                self.violations.append({
                    "type": "missing_required_file",
                    "message": f"Missing required file: {required}",
                })

    def _validate_file(self, file_path: Path) -> None:
        suffix = file_path.suffix.lower()
        name_lower = file_path.name.lower()

        is_allowed = (
            suffix in self.ALLOWED_EXTENSIONS or
            name_lower == "dockerfile" or
            name_lower in {"requirements.txt", "setup.py", "pyproject.toml"}
        )

        if not is_allowed:
            self.violations.append({
                "type": "disallowed_extension",
                "file": str(file_path),
                "message": f"Disallowed file type: {suffix or file_path.name}",
            })

        size_mb = file_path.stat().st_size / (1024 * 1024)
        if size_mb > self.MAX_FILE_SIZE_MB:
            self.violations.append({
                "type": "file_too_large",
                "file": str(file_path),
                "message": f"File size {size_mb:.2f}MB exceeds {self.MAX_FILE_SIZE_MB}MB",
            })

    def is_valid(self, directory: Path) -> bool:
        violations = self.validate_directory(directory)
        return len(violations) == 0
