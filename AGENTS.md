# Repository Guidelines

## Project Structure & Module Organization
`README.md` is the single source for adopters—refresh it whenever behavior changes. The primary reusable workflow for this repo is `.github/workflows/agents-codex.yml` (Codex Action). Use `examples/agents-codex-consumer.yml` and `examples/agents-apply-on-label.yml` to demonstrate usage. A Python fallback exists under `.github/workflows/agents.yml` + `scripts/update_agents.py`.

## Build, Test, and Development Commands
For Codex Action workflows, no local setup is needed. For the Python fallback, bootstrap with `python -m pip install --upgrade pip` then `pip install "openai>=1.35.0" requests`. Optional: `python -m compileall scripts` before pushing. Store mock suggestions/policies under `examples/` and reference them from docs.

## Coding Style & Naming Conventions
Follow PEP 8 with four-space indents, snake_case functions, and CONSTANT_CASE module globals. Keep API calls in small helpers and prefer guard clauses to nested branching. Format with `black scripts` and lint with `ruff check scripts`; commit their configs if defaults need adjusting. YAML should remain two-space indented with lowercase job ids and kebab-case step names.

## Testing Guidelines
There is no dedicated suite yet—favor quick feedback loops. Store mock suggestions/policies in `examples/` and document observed outputs in PRs (screenshots or copied comments). When logic grows, introduce `pytest` under `tests/` and ensure new functions are covered, especially failure paths in the Python fallback.

## Commit & Pull Request Guidelines
Stick to Conventional Commit headers (`feat:`, `fix:`, `chore:`, `docs:`). PRs should clearly state motivation, high-level changes, and test evidence (manual run, screenshots). Link related issues in the description or commit footer, update `README.md`/`examples/` when behavior changes, and request a peer review before merging.

## Security & Configuration Tips
Never echo `OPENAI_API_KEY`, `GITHUB_TOKEN`, or caller secrets; use throwaway values for local runs and clear shell history after use. Default new workflow inputs conservatively so downstream repos cannot escalate privileges. Retag `v1` only after validating breaking changes with at least one consumer repository.
