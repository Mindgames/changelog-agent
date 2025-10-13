# Repository Guidelines

## Project Structure & Module Organization
`README.md` is the single source for adopters—refresh it whenever behavior changes. The reusable workflow lives in `.github/workflows/changelog.yml`; it shells into `scripts/gen_changelog.py` for OpenAI calls and changelog edits. Use `examples/consumer-workflow.yml` to demonstrate new inputs, and rebuild the optional runtime in `docker/Dockerfile` when extra system tools are required.

## Build, Test, and Development Commands
Bootstrap dependencies with `python -m pip install --upgrade pip` then `pip install "openai>=1.35.0" requests`. Dry-run the changelog helper by exporting stub env vars (`REPO`, `PR_NUMBER`, `GITHUB_TOKEN`, `OPENAI_API_KEY`, `CHANGELOG_PATH`) and executing `python scripts/gen_changelog.py`. Run `python -m compileall scripts` before pushing, `docker build -t changelog-bot:dev docker` for image updates, and `act pull_request --job run` whenever you touch workflow logic.

## Coding Style & Naming Conventions
Follow PEP 8 with four-space indents, snake_case functions, and CONSTANT_CASE module globals. Keep API calls in small helpers and prefer guard clauses to nested branching. Format with `black scripts` and lint with `ruff check scripts`; commit their configs if defaults need adjusting. YAML should remain two-space indented with lowercase job ids and kebab-case step names.

## Testing Guidelines
There is no dedicated suite yet—favor quick feedback loops. Store mock payloads or changelog fixtures in `examples/` and reference them from `act` runs. When logic grows, introduce `pytest` under `tests/` and ensure new functions are covered, especially failure paths. Document observed outputs in PRs and attach the generated changelog diff for reviewers.

## Commit & Pull Request Guidelines
Stick to Conventional Commit headers (`feat:`, `fix:`, `chore:`, `docs:`) in line with the automated `chore(release): ...` commits. PRs should clearly state motivation, high-level changes, and test evidence (`act`, manual run, screenshots). Link related issues in the description or commit footer, update `README.md`/`examples/` when behavior changes, and request a peer review before merging.

## Security & Configuration Tips
Never echo `OPENAI_API_KEY`, `GITHUB_TOKEN`, or caller secrets; use throwaway values for local runs and clear shell history after use. Default new workflow inputs conservatively so downstream repos cannot escalate privileges. Retag `v1` only after validating breaking changes with at least one consumer repository.
