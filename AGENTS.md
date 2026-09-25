# Repository Guidelines

## Project Structure & Module Organization
`README.md` is the single source for adopters—refresh it whenever behavior changes. The reusable workflows `.github/workflows/agents-codex.yml` and `.github/workflows/agents.yml` are disabled compatibility shims. They report the disabled state without calling OpenAI or editing AGENTS.md. The older examples and `scripts/update_agents.py` are historical references only; see README.md for current behavior.

## Build, Test, and Development Commands
The active workflows are disabled compatibility shims and need no local setup. For historical Python code, use `python -m compileall scripts` if changing it. Store mock suggestions/policies under `examples/` and reference them from docs.

## Coding Style & Naming Conventions
Follow PEP 8 with four-space indents, snake_case functions, and CONSTANT_CASE module globals. Keep API calls in small helpers and prefer guard clauses to nested branching. Format with `black scripts` and lint with `ruff check scripts`; commit their configs if defaults need adjusting. YAML should remain two-space indented with lowercase job ids and kebab-case step names.

## Testing Guidelines
There is no dedicated suite yet—favor quick feedback loops. Store mock suggestions/policies in `examples/` and document observed outputs in PRs (screenshots or copied comments). When logic grows, introduce `pytest` under `tests/` and ensure new functions are covered, especially failure paths in the Python fallback.

## Commit & Pull Request Guidelines
Stick to Conventional Commit headers (`feat:`, `fix:`, `chore:`, `docs:`). PRs should clearly state motivation, high-level changes, and test evidence (manual run, screenshots). Link related issues in the description or commit footer, update `README.md`/`examples/` when behavior changes, and request a peer review before merging.

## Security & Configuration Tips
Never echo `OPENAI_API_KEY`, `GITHUB_TOKEN`, or caller secrets; use throwaway values for local runs and clear shell history after use. Default new workflow inputs conservatively so downstream repos cannot escalate privileges. Do not retag `v1` without validating consumers; older refs still point to API-backed code.
