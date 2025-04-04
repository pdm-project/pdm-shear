from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import rich

from pdm_shear.parser import ImportStatement


class FixAction(Protocol):
    def __call__(self, data: dict[str, Any]) -> None:
        """Fix the data in place."""
        ...


@dataclass(frozen=True)
class UnusedDependency:
    """Remove a dependency from the project."""

    dependency: str

    def __call__(self, data: dict[str, Any]) -> None:
        if (
            "dependencies" in data.get("project", {})
            and self.dependency in data["project"]["dependencies"]
        ):
            data["project"]["dependencies"].remove(self.dependency)
            rich.print(f"Removed dependency: [green bold]{self.dependency}[/]")

    def __rich__(self) -> str:
        return f"Found unused dependency: [green bold]{self.dependency}[/]"


@dataclass(frozen=True)
class UnusedOptionalDependency:
    """Remove an optional dependency from the project."""

    dependency: str
    group: str

    def __call__(self, data: dict[str, Any]) -> None:
        if (
            "optional-dependencies" in data.get("project", {})
            and self.group in data["project"]["optional-dependencies"]
        ):
            group = data["project"]["optional-dependencies"][self.group]
            if self.dependency in group:
                group.remove(self.dependency)
                rich.print(
                    f"Removed optional dependency of group [yellow]{self.group}[/]: [green bold]{self.dependency}[/]"
                )

    def __rich__(self) -> str:
        return f"Found unused optional dependency of group [yellow]{self.group}[/]: [green bold]{self.dependency}[/]"


@dataclass(frozen=True)
class MissingDependency:
    """Missing dependency."""

    module_name: str
    statements: list[ImportStatement]

    def __rich__(self) -> str:
        text = f"Missing dependency: [green bold]{self.module_name}[/] used by the following files:"
        for stm in self.statements:
            text += f"\n{stm.__rich__()}"
        return text

    def __call__(self, data: dict[str, Any]) -> None:
        rich.print(self)
