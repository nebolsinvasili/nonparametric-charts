# AGENTS.md

"ShCC" — Python library for Shewhart (control) chart analysis of multivariate data.
Code, comments, docstrings, and chart labels are **in Russian** — keep them that way.
Research repo: no git, no CI, no README; `poetry.lock` is generated but gitignored.

## Layout and imports

- Source lives in three top-level subpackages under `src/` (there is **no** `src/ShCC/`, no `src/__init__.py`):
  - `src/base/base_chart.py` — abstract `BaseControlChart` (control limits, Western-Electric zones, plot helpers)
  - `src/charts/` — `XBarChart`, `RChart`, `SChart`, `MedianChart`, `SignChart`, `SignedRankChart` (all extend `BaseControlChart`)
  - `src/utils/` — `DataLoader`, `DataPreprocessor`, `DataPipeline`, `plotting`, `coefficients.json`
- All modules use absolute `from src.{base,charts,utils}.` imports. Run everything **from the repo root** with the root on `sys.path` — it is not an installed package. `config/`, `.env` are empty placeholders.

## Poetry environment

Poetry manages deps (`pyproject.toml`, `[tool.poetry] package-mode = false` — no `ShCC` package, no `shukart-*` scripts, no `import ShCC`). Setup: `poetry install --with dev`, activate with `poetry env activate`. Jupyter kernel for notebooks: `shcc-py` (`poetry run python -m ipykernel install --user --name shcc-py`). Tests live in `tests/` (see `tests/xbar/` for a worked book example).

## Coefficients file

`BaseControlChart._load_coefficients` searches paths that do **not** include the real `src/utils/coefficients.json`. Always pass `coefficients_file='src/utils/coefficients.json'` (repo-root-relative) or set `SHCC_COEFFICIENTS`. Notebooks pass `'../src/utils/coefficients.json'`.

## Data model

- Each row is one subgroup, each column one measurement, so `sample_size` = number of columns (not rows). Sample data: `data/data.csv` (14 columns, n=14).
- `DataLoader` auto-detects separators/encodings and converts comma decimals.
- `DataPreprocessor` auto-strips a leading 1..N index column if present.

## Notebooks

`notebooks/*.ipynb` (gitignored) are the working entrypoints. Run them **from inside `notebooks/`** — they `sys.path.append('..')` and reference `../data/data.csv` and `../src/utils/coefficients.json`. Reuse this pattern rather than relocating.

## Environment

- Requires Python >=3.14 (`.python-version`: 3.14.6). Install everything with `poetry install --with dev` (main: pandas>=3, numpy>=2.5, scipy, matplotlib; dev: pytest, black, flake8, isort, mypy, jupyter). Do not pip-install alongside poetry.
- pytest is configured (`testpaths=["tests"]`, `python_files="test_*.py"`). Add tests in `tests/` (use a per-chart subfolder, e.g. `tests/xbar/`) when changing logic.