"""
pdm_shear

:Please add description here:
"""

from __future__ import annotations

from argparse import ArgumentParser, Namespace

from pdm.cli.commands.base import BaseCommand
from pdm.core import Core
from pdm.project import Project


class ShearCommand(BaseCommand):
    """Detect and remove unused dependencies for Python projects"""

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--fix",
            action="store_true",
            help="Fix the pyproject.toml to remove the unused dependencies",
        )
        parser.add_argument(
            "--ignore-missing-deps",
            action="store_true",
            help="Ignore missing dependencies",
        )

    def handle(self, project: Project, options: Namespace) -> None:
        from pdm_shear.main import fix_or_show_unused_dependencies

        result = fix_or_show_unused_dependencies(
            project, options.fix, options.ignore_missing_deps
        )
        raise SystemExit(int(not result))


def plugin(core: Core) -> None:
    """Register pdm plugin to pdm-core."""
    core.register_command(ShearCommand, "shear")
