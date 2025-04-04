import textwrap

pytest_plugins = ["pdm.pytest"]


def test_unused_deps(pdm, mock_data, project):
    project.pyproject.metadata["dependencies"] = ["requests", "flask"]
    project.pyproject.metadata["optional-dependencies"] = {
        "web": ["django"],
    }
    project.pyproject.write()
    project.root.joinpath("test.py").write_text(
        textwrap.dedent(
            """\
        import requests as req
        from django.conf import settings
        import rich
        """
        )
    )
    result = pdm(["shear"], obj=project)
    assert result.exit_code == 1
    assert "Found unused dependency: flask" in result.stdout
    assert "Found unused dependency: requests" not in result.stdout
    assert "Found unused optional dependency of group web: django" not in result.stdout

    result = pdm(["shear", "--fix"], obj=project)
    assert result.exit_code == 1
    assert "Removed dependency: flask" in result.stdout
    assert project.pyproject.metadata["dependencies"] == ["requests"]


def test_missing_deps(pdm, mock_data, project):
    project.pyproject.metadata["dependencies"] = ["requests"]
    project.pyproject.write()
    project.root.joinpath("test.py").write_text(
        textwrap.dedent(
            """\
        import requests
        from django.conf import settings
        import rich
        """
        )
    )
    result = pdm(["shear"], obj=project)
    assert result.exit_code == 1
    assert "Missing dependency: django" in result.stdout
    assert "Missing dependency: rich" in result.stdout

    result = pdm(["shear", "--ignore-missing-deps"], obj=project)
    assert result.exit_code == 0

    project.pyproject._data.setdefault("tool", {}).setdefault("pdm", {})["shear"] = {
        "ignore_missing_deps": True
    }
    project.pyproject.write()
    result = pdm(["shear"], obj=project)
    assert result.exit_code == 0
