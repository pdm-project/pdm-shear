from __future__ import annotations

import csv
import json
import subprocess
import zipfile
from itertools import groupby
from typing import TYPE_CHECKING, Iterable

import rich

from pdm_shear.actions import (
    FixAction,
    MissingDependency,
    UnusedDependency,
    UnusedOptionalDependency,
)
from pdm_shear.parser import get_project_imports

if TYPE_CHECKING:
    from pdm.project import Project


def filter_site_packages(project: Project, module_names: list[str]) -> list[str]:
    """Return a list of module names that are installed in site-packages."""
    script = f"""\
import json
import importlib.util
module_names = {module_names!r}
site_packages = []
for module_name in module_names:
    try:
        spec = importlib.util.find_spec(module_name)
    except ModuleNotFoundError:
        site_packages.append(module_name)
        continue
    if not spec or spec.origin and "site-packages" in spec.origin:
        site_packages.append(module_name)
print(json.dumps(site_packages))
"""
    try:
        result = subprocess.run(
            [str(project.environment.interpreter.path), "-c", script],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to run Python script: {e.stderr}") from e
    else:
        return json.loads(result.stdout)


_local_cache: dict[str, list[str]] = {}


def get_top_level_names(project: Project, dependency: str) -> list[str]:
    """Get the top-level names of the distribution."""
    from pdm.exceptions import ProjectError
    from pdm.models.caches import JSONFileCache
    from pdm.models.candidates import Candidate
    from pdm.models.requirements import parse_requirement

    req = parse_requirement(dependency)
    working_set = project.environment.get_working_set()
    dist_name = req.key
    if not dist_name:
        raise ProjectError(f"Dependency name must be given: {dependency!r}")
    # 0. Check local cache
    if dist_name in _local_cache:
        return _local_cache[dist_name]
    # 1. Get from installed package
    if dist_name in working_set:
        dist = working_set[dist_name]
        if top_level := dist.read_text("top_level.txt"):
            result = top_level.splitlines()
        else:
            result = _collect_top_level_names(
                path.as_posix() for path in dist.files or []
            )
        _local_cache[dist_name] = result
        return result
    # 2. Get from cache file
    cache = JSONFileCache(project.cache_dir / "top_level_names.json")
    if project.core.state.enable_cache and dist_name in cache:
        cached = cache.get(dist_name)
        _local_cache[dist_name] = cached
        return cached
    # 3. Get from PyPI wheel
    with project.environment.get_finder() as finder:
        best_match = finder.find_best_match(dependency)
        if not best_match.best:
            raise ProjectError(f"Cannot find distribution for {dependency!r}")
        candidate = Candidate.from_installation_candidate(best_match.best, req)
        prepared = candidate.prepare(project.environment)
        wheel = prepared.build()
        with zipfile.ZipFile(wheel, "r") as zf:
            record_file = next(
                f for f in zf.namelist() if f.endswith(".dist-info/RECORD")
            )

            record_lines = zf.read(record_file).decode("utf-8").splitlines()
            top_level_names = _collect_top_level_names(
                name for name, *_ in csv.reader(record_lines)
            )
            cache.set(dist_name, top_level_names)
            _local_cache[dist_name] = top_level_names
            return top_level_names


def _collect_top_level_names(paths: Iterable[str]) -> list[str]:
    top_level_names: set[str] = set()
    for path in paths:
        if path.startswith("."):
            continue
        if not path.endswith((".py", ".pyi", ".pyc", ".pyd", ".pyo", ".so")):
            continue
        top_name = path.split("/")[0].split(".")[0]
        top_level_names.add(top_name)
    return list(top_level_names)


def fix_or_show_unused_dependencies(
    project: Project, fix: bool = False, ignore_missing_deps: bool = False
) -> bool:
    from pdm.utils import normalize_name

    data = project.pyproject.read()
    tool_config = data.get("tool", {}).get("pdm", {}).get("shear", {})
    imports = sorted(
        get_project_imports(
            project.root, tool_config.get("include"), tool_config.get("exclude")
        )
    )
    grouped = {k: list(v) for k, v in groupby(imports, key=lambda x: x.module)}
    used_names = filter_site_packages(project, list(grouped.keys()))
    used_grouped = {k: v for k, v in grouped.items() if k in used_names}

    actions: list[FixAction] = []
    for dep in project.pyproject.metadata.get("dependencies", []):
        top_names = get_top_level_names(project, dep)
        if set(top_names).isdisjoint(used_names):
            actions.append(UnusedDependency(dependency=dep))
        else:
            for name in top_names:
                used_grouped.pop(name, None)

    for group, deps in project.pyproject.metadata.get(
        "optional-dependencies", {}
    ).items():
        for dep in deps:
            top_names = get_top_level_names(project, dep)
            if set(top_names).isdisjoint(used_names):
                actions.append(UnusedOptionalDependency(dependency=dep, group=group))
            else:
                for name in top_names:
                    used_grouped.pop(name, None)
    if not ignore_missing_deps and not tool_config.get("ignore_missing_deps", False):
        for name, statements in used_grouped.items():
            if project.name and normalize_name(project.name) == name:
                continue
            actions.append(
                MissingDependency(module_name=name, statements=sorted(statements))
            )

    if fix:
        for action in actions:
            action(data)
        project.pyproject.set_data(data)
        project.pyproject.write()
    else:
        for action in actions:
            rich.print(action)
    if any(isinstance(action, MissingDependency) for action in actions):
        rich.print(
            "[yellow]Add them to the dependencies or ignore the warning with `--ignore-missing-deps`[/]"
        )
    return len(actions) == 0
