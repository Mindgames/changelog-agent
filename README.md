# Agents Updater (disabled)

The OpenAI-backed AGENTS.md updater is disconnected in this repository. The reusable workflows `.github/workflows/agents-codex.yml` and `.github/workflows/agents.yml` remain callable for compatibility, but only report that the updater is disabled. They do not inspect a PR, create suggestions, edit files, post comments, or require an OpenAI API key. The repository's PR and label workflows invoke the local disabled workflow.

A successful workflow run means only that the disabled state was reported. It is not an AGENTS.md review. Review AGENTS.md changes manually until a replacement workflow is approved.

Consumers pinned to an older tag or commit still execute that older version. Update their workflow reference to `@main` or another disabled revision to stop those calls; this repository's change cannot alter immutable refs already used elsewhere.
