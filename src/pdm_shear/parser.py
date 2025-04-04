from __future__ import annotations

import ast
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class ImportStatement:
    module: str
    file_path: Path
    line_number: int
    col_offset: int
    end_col_offset: int

    def _comp_key(self) -> tuple[str, str, int, int]:
        """Comparison key for sorting."""
        return (
            self.module,
            self.file_path.as_posix(),
            self.line_number,
            self.col_offset,
        )

    def __lt__(self, other: ImportStatement) -> bool:
        """Less than comparison for sorting."""
        return self._comp_key() < other._comp_key()

    def __rich__(self) -> str:
        """Rich representation for display."""
        with open(self.file_path) as file:
            line = file.readlines()[self.line_number - 1].rstrip()
        rendered = f"{line[: self.col_offset]}[red]{line[self.col_offset : self.end_col_offset]}[/]{line[self.end_col_offset :]}"
        return f"{self.file_path}:{self.line_number}\n{rendered}"


def _parse_imports_single_file(file_path: Path) -> Iterable[ImportStatement]:
    """Parse the given Python source file to detect imports."""

    with open(file_path, "r") as file:
        node = ast.parse(file.read(), filename=file_path)

    for n in ast.walk(node):
        if isinstance(n, ast.Import):
            for alias in n.names:
                if not alias.name:
                    continue
                yield ImportStatement(
                    module=alias.name.split(".")[0],
                    file_path=file_path,
                    line_number=alias.lineno,
                    col_offset=alias.col_offset,
                    end_col_offset=alias.end_col_offset,
                )
        elif (
            isinstance(n, ast.ImportFrom) and n.module
        ):  # relative import may not have module name
            yield ImportStatement(
                module=n.module.split(".")[0],
                file_path=file_path,
                line_number=n.lineno,
                col_offset=n.col_offset,
                end_col_offset=n.end_col_offset,
            )


DEFAULT_EXCLUDE = [".venv/*"]


def get_project_imports(
    project_path: Path,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
) -> Iterable[ImportStatement]:
    """Get all imports from the project directory."""
    if not project_path.is_dir():
        raise ValueError(f"Path {project_path} is not a directory.")
    for path in project_path.rglob("*.py"):
        rel_path = path.relative_to(project_path).as_posix()
        if any(fnmatchcase(rel_path, pattern) for pattern in DEFAULT_EXCLUDE):
            continue
        if include is not None and not any(
            fnmatchcase(rel_path, pattern) for pattern in include
        ):
            continue
        if exclude is not None and any(
            fnmatchcase(rel_path, pattern) for pattern in exclude
        ):
            continue
        yield from _parse_imports_single_file(path)
