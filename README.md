# Agents Updater (Codex Action)

A reusable GitHub Actions workflow that uses OpenAI Codex Action to keep `AGENTS.md` files current as your code changes. It proposes edits on every PR and can auto-apply them on demand.

## Agents Updater (PoC)

This repo ships a Codex-powered, reusable workflow that keeps `AGENTS.md` files up to date on every PR. It proposes changes by default, and can auto-apply them with a single label or a separate job.

- Reusable (Codex Action): `.github/workflows/agents-codex.yml`
- Example (suggest): `examples/agents-codex-consumer.yml`
- Example (apply on label): `examples/agents-apply-on-label.yml`
- Optional Python fallback: `.github/workflows/agents.yml` + `scripts/update_agents.py`

How it works
- Runs on PRs to analyze changed files and target the nearest `AGENTS.md` (primary) plus parent `AGENTS.md` (secondary).
- Preserves tone/structure and makes minimal, actionable edits.
- Enforces a caller-provided block (e.g., “xyz”) exactly once in each updated file.
- Modes:
  - suggest (default): read-only sandbox, outputs a JSON plan and posts a summary comment.
  - apply: workspace-write sandbox, applies edits on disk, validates only AGENTS.md changed, and commits.

Quick start (suggest)
```yaml
name: agents
on:
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review]
permissions:
  contents: write
  pull-requests: write
jobs:
  agents-updater:
    uses: your-org/changelog-bot/.github/workflows/agents-codex.yml@v1
    secrets: inherit
    with:
      mode: suggest
      always_include: "xyz"
      model: gpt-4o-mini
```

One‑click apply via label
```yaml
name: agents-apply
on:
  pull_request:
    types: [labeled]
permissions:
  contents: write
  pull-requests: write
jobs:
  apply:
    if: contains(github.event.pull_request.labels.*.name, 'agents:apply')
    uses: your-org/changelog-bot/.github/workflows/agents-codex.yml@v1
    secrets: inherit
    with:
      mode: apply
      always_include: "xyz"
      model: gpt-4o-mini
```

Policy (optional)
- Add `.codex/agents-policy.toml` to guide edits (see `examples/agents-policy.toml`).
- Suggested keys: `required_blocks[]`, `parent_update_strategy`, `allow_parent_writes`, `section_order[]`, `prohibited_phrases[]`, `max_edits_per_run`.

Safety & guarantees
- `openai/codex-action@v1` with default `drop-sudo` and a sandbox.
- Apply mode validates that only `**/AGENTS.md` files changed; the job fails otherwise.
- For same-repo branches, changes push directly to the PR branch; otherwise, a small bot PR is opened.

Notes
- The updater prioritizes the nearest `AGENTS.md` and also considers parent `AGENTS.md` for higher-level guidance.
- Secrets are never echoed; provide them via env vars and avoid printing values.

## Security notes
- Runs as the caller repo with `contents: write` + `pull-requests: write` only.
- Avoids `pull_request_target` (no escalated token from forks).
- Apply mode validates only `AGENTS.md` paths mutate before committing.
