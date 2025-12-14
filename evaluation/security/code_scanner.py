import ast
import re
from pathlib import Path
from typing import List, Set

from loguru import logger


class CodeScanner:
    DANGEROUS_IMPORTS: Set[str] = {
        "subprocess",
        "os",
        "sys",
        "socket",
        "requests",
        "urllib",
        "http",
        "ftplib",
        "smtplib",
        "paramiko",
        "fabric",
        "pexpect",
        "pty",
        "ctypes",
        "multiprocessing",
        "threading",
        "asyncio",
        "aiohttp",
        "httpx",
    }

    DANGEROUS_CALLS: Set[str] = {
        "exec",
        "eval",
        "compile",
        "open",
        "__import__",
        "getattr",
        "setattr",
        "delattr",
        "globals",
        "locals",
        "vars",
        "input",
    }

    DANGEROUS_PATTERNS: List[str] = [
        r"import\s+os",
        r"from\s+os\s+import",
        r"subprocess\.run",
        r"subprocess\.Popen",
        r"subprocess\.call",
        r"os\.system",
        r"os\.popen",
        r"os\.exec",
        r"socket\.socket",
        r"requests\.get",
        r"requests\.post",
        r"urllib\.request",
        r"http\.client",
        r"open\s*\([^)]*['\"][wax]",
        r"__builtins__",
        r"__class__",
        r"__mro__",
        r"__subclasses__",
    ]

    def __init__(self):
        self.violations: List[dict] = []

    def scan_file(self, file_path: Path) -> List[dict]:
        self.violations = []

        content = file_path.read_text(encoding="utf-8", errors="ignore")

        self._scan_patterns(content, file_path)

        try:
            tree = ast.parse(content)
            self._scan_ast(tree, file_path)
        except SyntaxError as e:
            self.violations.append({
                "file": str(file_path),
                "type": "syntax_error",
                "message": str(e),
                "line": e.lineno,
            })

        return self.violations

    def _scan_patterns(self, content: str, file_path: Path) -> None:
        for pattern in self.DANGEROUS_PATTERNS:
            for match in re.finditer(pattern, content):
                line_num = content[:match.start()].count("\n") + 1
                self.violations.append({
                    "file": str(file_path),
                    "type": "dangerous_pattern",
                    "message": f"Matched pattern: {pattern}",
                    "line": line_num,
                })

    def _scan_ast(self, tree: ast.AST, file_path: Path) -> None:
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name.split(".")[0]
                    if module in self.DANGEROUS_IMPORTS:
                        self.violations.append({
                            "file": str(file_path),
                            "type": "dangerous_import",
                            "message": f"Import of {alias.name}",
                            "line": node.lineno,
                        })

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module = node.module.split(".")[0]
                    if module in self.DANGEROUS_IMPORTS:
                        self.violations.append({
                            "file": str(file_path),
                            "type": "dangerous_import",
                            "message": f"Import from {node.module}",
                            "line": node.lineno,
                        })

            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in self.DANGEROUS_CALLS:
                        self.violations.append({
                            "file": str(file_path),
                            "type": "dangerous_call",
                            "message": f"Call to {node.func.id}",
                            "line": node.lineno,
                        })

    def scan_directory(self, directory: Path) -> List[dict]:
        all_violations = []

        for py_file in directory.rglob("*.py"):
            violations = self.scan_file(py_file)
            all_violations.extend(violations)

        logger.info(
            "code_scan_complete",
            directory=str(directory),
            files_scanned=len(list(directory.rglob("*.py"))),
            violations_found=len(all_violations),
        )

        return all_violations

    def is_safe(self, directory: Path) -> bool:
        violations = self.scan_directory(directory)
        return len(violations) == 0
