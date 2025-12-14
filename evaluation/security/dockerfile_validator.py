import re
from pathlib import Path
from typing import List

from loguru import logger


class DockerfileValidator:
    FORBIDDEN_INSTRUCTIONS: List[str] = [
        r"--privileged",
        r"--cap-add",
        r"--security-opt.*unconfined",
        r"host\.docker\.internal",
        r"docker\.sock",
        r"SYS_ADMIN",
        r"SYS_PTRACE",
        r"NET_ADMIN",
        r"--net=host",
        r"--network=host",
        r"--pid=host",
        r"--ipc=host",
    ]

    ALLOWED_BASE_IMAGES: List[str] = [
        r"^python:[0-9]+\.[0-9]+",
        r"^python:[0-9]+\.[0-9]+-slim",
        r"^python:[0-9]+\.[0-9]+-alpine",
    ]

    def __init__(self):
        self.violations: List[dict] = []

    def validate(self, dockerfile_path: Path) -> List[dict]:
        self.violations = []

        if not dockerfile_path.exists():
            raise ValueError(f"dockerfile_not_found: {dockerfile_path}")

        content = dockerfile_path.read_text()
        lines = content.split("\n")

        self._check_forbidden_instructions(content)
        self._check_base_image(lines)
        self._check_user_directive(lines)

        logger.info(
            "dockerfile_validated",
            path=str(dockerfile_path),
            violations_found=len(self.violations),
        )

        return self.violations

    def _check_forbidden_instructions(self, content: str) -> None:
        for pattern in self.FORBIDDEN_INSTRUCTIONS:
            if re.search(pattern, content, re.IGNORECASE):
                self.violations.append({
                    "type": "forbidden_instruction",
                    "message": f"Found forbidden pattern: {pattern}",
                })

    def _check_base_image(self, lines: List[str]) -> None:
        for line in lines:
            line = line.strip()
            if line.upper().startswith("FROM "):
                image = line[5:].strip().split()[0]

                is_allowed = any(
                    re.match(pattern, image)
                    for pattern in self.ALLOWED_BASE_IMAGES
                )

                if not is_allowed:
                    self.violations.append({
                        "type": "disallowed_base_image",
                        "message": f"Base image not in allowlist: {image}",
                    })
                return

        self.violations.append({
            "type": "missing_from",
            "message": "No FROM instruction found",
        })

    def _check_user_directive(self, lines: List[str]) -> None:
        has_user = any(
            line.strip().upper().startswith("USER ")
            for line in lines
        )

        if not has_user:
            self.violations.append({
                "type": "missing_user",
                "message": "No USER directive - container may run as root",
            })

    def is_valid(self, dockerfile_path: Path) -> bool:
        violations = self.validate(dockerfile_path)
        return len(violations) == 0
