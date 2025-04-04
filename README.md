# pdm-shear

> Detect and remove unused dependencies for Python projects

## Installation

Enable the plugin:

```bash
pdm self add pdm-shear
```

Enable the plugin in your project:

```toml
[tool.pdm]
plugins = ["pdm-shear"]
```

And run the following command once in your project:

```bash
pdm install --plugins
```

## Usage

Run the shear command to analyze dependencies:

```bash
pdm shear
```

This will show you a report of:
- Unused direct dependencies
- Unused optional dependencies
- Missing dependencies (if enabled)

### Options

- `--fix`: Remove the unused dependencies from pyproject.toml automatically
- `--ignore-missing-deps`: Don't report missing dependencies

### Configuration

In `pyproject.toml`, you can configure the plugin behavior:

```toml
[tool.pdm.shear]
# Paths to include in the analysis (glob patterns)
include = ["src/*.py", "tests/*.py"]
# Paths to exclude from the analysis (glob patterns)
exclude = ["tests/fixtures/*.py"]
# Don't show missing dependencies warnings
ignore_missing_deps = true
```

## How It Works

pdm-shear analyzes your Python source code to:
1. Find all import statements and their locations
2. Compare them against your declared dependencies
3. Identify dependencies that aren't used in your code
4. Optionally detect imports that don't map to any dependency

## License

MIT
