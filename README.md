# changelog-bot

Central, reusable workflow to:
1. **Bump versions** (Python or pnpm) after a PR is merged to `main`
2. **Append a Keep a Changelog entry** for that PR to the root `CHANGELOG.md`

## How to use

1. Create the repo (example name): **`your-org/changelog-bot`** and push these files.
2. Tag a stable major version (e.g., `v1`) so consumers can pin:
   ```bash
   git tag -f v1 && git push -f origin v1
   ```
3. Add an **org secret** `OPENAI_API_KEY` so all consumer repos can `secrets: inherit`.
4. In each consumer repo, add this workflow (see `examples/consumer-workflow.yml`):
   ```yaml
   name: changelog
   on:
     pull_request:
       types: [closed]
       branches: [main]
   permissions:
     contents: write
     pull-requests: write
   jobs:
     changelog:
       uses: your-org/changelog-bot/.github/workflows/changelog.yml@v1
       secrets: inherit
       with:
         project_type: auto
         bump_from_labels: false
         bump_level: patch
         changelog_path: CHANGELOG.md
         openai_model: gpt-4o-mini
         openai_base_url: ""
         central_repo: your-org/changelog-bot
         central_ref: v1
   ```

> **Note:** Replace `your-org` with your real org. Keep callers pinned to `@v1`. When you improve this bot, retag `v1` to roll out updates globally.

## Inputs (consumers can override)

- `project_type`: `auto|python|pnpm` (default `auto`)
- `bump_from_labels`: `true|false` (default `false`) — if true, infer semver level from labels
- `label_major|label_minor|label_patch`: label names (defaults: `semver:major`, `semver:minor`, `semver:patch`)
- `bump_level`: `patch|minor|major` (default `patch`, ignored if `bump_from_labels=true`)
- `changelog_path`: path to root changelog (default `CHANGELOG.md`)
- `openai_model`: model name (default `gpt-4o-mini`)
- `openai_base_url`: custom OpenAI-compatible endpoint (optional)
- `central_repo`: repo that hosts this workflow & script (default `your-org/changelog-bot`)
- `central_ref`: git ref to check out scripts from (default `v1`)

## What it does (high level)
- Triggers only when a PR is **merged into `main`**.
- Detects repo type or uses forced input.
- Bumps version:
  - Python: `python scripts/bump_version.py --{patch|minor|major}`
  - pnpm: `pnpm version {patch|minor|major} --no-git-tag-version` + `pnpm install --lockfile-only`
- Calls an LLM to generate a single bullet (Keep a Changelog categories).
- Inserts under `## [Unreleased]` → appropriate `### Category`.
- Opens a **bot PR** with both the version bump and changelog change.

## Optional: pinned runtime via GHCR
If you want deterministic toolchains, build the Docker image in `/docker` using the workflow `publish-image.yml`, then add to `jobs.run:` in `changelog.yml`:
```yaml
container:
  image: ghcr.io/${{ github.repository_owner }}/changelog-bot:1
```
You can bump the tag and re-pin callers when needed.

## Security notes
- Runs as the **caller repo** with `contents: write` + `pull-requests: write` only.
- Avoids `pull_request_target` (no escalated token from forks).
- Idempotent: skips if the PR number is already present in `CHANGELOG.md`.
