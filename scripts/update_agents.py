import os
import json
import pathlib
import re
import sys
from typing import Dict, List, Tuple

import requests


# --- Env & constants ---------------------------------------------------------
REPO = os.environ["REPO"]  # org/name
OWNER, NAME = REPO.split("/")
PR_NUMBER = int(os.environ["PR_NUMBER"])  # running on an open PR

GH_API = "https://api.github.com"
GH_HEADERS = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
}

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-codex")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")

# PoC configuration: suggestion vs apply
MODE = os.getenv("AGENTS_MODE", "suggest").strip().lower()  # suggest|apply

# Required text or block that must appear in every AGENTS.md this script touches
ALWAYS_INCLUDE = os.getenv("AGENTS_ALWAYS_INCLUDE", "xyz").strip()
ALWAYS_INCLUDE_FILE = os.getenv("AGENTS_ALWAYS_INCLUDE_FILE", "").strip()

if ALWAYS_INCLUDE_FILE:
    p = pathlib.Path(ALWAYS_INCLUDE_FILE)
    if p.exists():
        ALWAYS_INCLUDE = p.read_text(encoding="utf-8")


def gh_get(url: str, params=None):
    r = requests.get(url, headers=GH_HEADERS, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def fetch_pr_context() -> Tuple[dict, List[dict]]:
    pr = gh_get(f"{GH_API}/repos/{OWNER}/{NAME}/pulls/{PR_NUMBER}")
    files = gh_get(f"{GH_API}/repos/{OWNER}/{NAME}/pulls/{PR_NUMBER}/files")
    return pr, files


def summarize_files(fs: List[dict], cap: int = 50) -> str:
    out = []
    for f in fs[:cap]:
        out.append(
            f"{f['status']} {f['filename']} (+{f['additions']}/-{f['deletions']})"
        )
    if len(fs) > cap:
        out.append(f"... and {len(fs) - cap} more")
    return "\n".join(out)


def map_changed_paths_to_agents(files: List[dict]) -> Dict[pathlib.Path, List[str]]:
    """Return mapping of AGENTS.md files (nearest + parents) -> impacted files.

    - For each changed path, include the nearest AGENTS.md (most relevant).
    - Also include any ancestor AGENTS.md files up to repo root (secondary attention).
    - If none are found, map to repo root AGENTS.md (may be created).
    """
    root = pathlib.Path(os.getenv("GITHUB_WORKSPACE", ".")).resolve()
    changed = [f["filename"] for f in files]

    mapping: Dict[pathlib.Path, List[str]] = {}

    for rel in changed:
        abs_path = (root / rel).resolve()
        # If the file was deleted/moved, path may not exist locally; use directory
        if not abs_path.exists():
            abs_path = (root / pathlib.Path(rel).parent).resolve()

        # Build chain of directories from nearest to root
        dirs: List[pathlib.Path] = []
        cur = abs_path if abs_path.is_dir() else abs_path.parent
        dirs.append(cur)
        dirs.extend(list(cur.parents))

        found_any = False
        for d in dirs:
            candidate = d / "AGENTS.md"
            if candidate.exists():
                mapping.setdefault(candidate, []).append(rel)
                found_any = True

        if not found_any:
            # fallback to root-level AGENTS.md
            candidate = root / "AGENTS.md"
            mapping.setdefault(candidate, []).append(rel)

    return mapping


def ensure_always_include_block(text: str, required: str) -> str:
    if not required.strip():
        return text
    if required.strip() in text:
        return text
    # Append a small section at the end
    sep = "\n\n" if text.endswith("\n") else "\n\n"
    return text + sep + required.strip() + "\n"


def build_prompt(
    file_path: str, current: str, changed_files_summary: str, always_include: str
) -> str:
    return f"""
You are updating a repository AGENTS.md file. Maintain its tone and structure, keep bullets concise.

Goals:
- Reflect notable changes implied by the impacted files.
- Clarify scope rules and any coding/run tips relevant to those files.
- Keep instructions actionable; avoid fluff.
- Preserve existing content unless adjustments are clearly beneficial.
- Ensure the following required block/snippet is included verbatim once:
\n{always_include}\n
Inputs
- File: {file_path}
- Impacted files (status path +/−):
{changed_files_summary}

Output strictly as JSON with fields:
{{
  "updated_content": "<full AGENTS.md content after edits>",
  "summary": "<1–2 lines summarizing the edits>"
}}

Existing content starts after this line:
--- BEGIN CURRENT AGENTS.md ---
{current}
--- END CURRENT AGENTS.md ---
""".strip()


def llm_update(agents_path: pathlib.Path, impacted: List[str], model: str) -> Tuple[str, str]:
    from openai import OpenAI

    client = OpenAI(base_url=OPENAI_BASE_URL or None, api_key=os.environ["OPENAI_API_KEY"])

    current = agents_path.read_text(encoding="utf-8") if agents_path.exists() else ""
    # Format impacted files nicely
    changed_files_summary = "\n".join(f"- {p}" for p in impacted)
    # Build prompt
    prompt = build_prompt(str(agents_path), current, changed_files_summary, ALWAYS_INCLUDE)

    schema = {
        "name": "AgentsUpdate",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "updated_content": {"type": "string"},
                "summary": {"type": "string", "maxLength": 280},
            },
            "required": ["updated_content", "summary"],
            "additionalProperties": False,
        },
    }

    try:
        resp = client.responses.create(
            model=model,
            input=prompt,
            response_format={"type": "json_schema", "json_schema": schema},
        )
        parsed = json.loads(resp.output_text)
        content = str(parsed["updated_content"]) if isinstance(parsed, dict) else ""
        summary = str(parsed.get("summary", "")) if isinstance(parsed, dict) else ""
    except Exception:
        # Fallback: keep current content, just enforce ALWAYS_INCLUDE
        content = current
        summary = "No LLM changes; enforced required block."

    # Enforce ALWAYS_INCLUDE block idempotently
    content = ensure_always_include_block(content or current, ALWAYS_INCLUDE)
    return content, summary


def post_pr_comment(body: str) -> None:
    url = f"{GH_API}/repos/{OWNER}/{NAME}/issues/{PR_NUMBER}/comments"
    r = requests.post(url, headers=GH_HEADERS, json={"body": body}, timeout=30)
    r.raise_for_status()


def main() -> None:
    root = pathlib.Path(os.getenv("GITHUB_WORKSPACE", ".")).resolve()
    pr, files = fetch_pr_context()

    if not files:
        print("No changed files in PR; nothing to do.")
        return

    mapping = map_changed_paths_to_agents(files)
    if not mapping:
        print("No AGENTS.md targets detected.")
        return

    any_applied = False
    report: List[dict] = []

    for agents_path, impacted in mapping.items():
        # Compute updated content via LLM + enforcement
        updated_content, rationale = llm_update(agents_path, impacted, OPENAI_MODEL)

        current = agents_path.read_text(encoding="utf-8") if agents_path.exists() else ""
        if updated_content.strip() == current.strip():
            report.append(
                {
                    "file": str(agents_path.relative_to(root)),
                    "changed": False,
                    "summary": rationale or "No changes",
                }
            )
            continue

        # Suggest: leave a PR comment with a patch preview
        rel = str(agents_path.relative_to(root))
        diff_header = f"Proposed update to `{rel}`"
        fenced_new = f"```markdown\n{updated_content}\n```"
        comment = (
            f"{diff_header}\n\nReasoning: {rationale or 'Proposed AGENTS.md refresh.'}\n\n"
            f"New file content preview:\n\n{fenced_new}"
        )

        # Apply or only suggest
        if MODE == "apply":
            agents_path.parent.mkdir(parents=True, exist_ok=True)
            agents_path.write_text(updated_content, encoding="utf-8")
            any_applied = True
            # Also post a short comment for visibility
            try:
                post_pr_comment(f"Applied AGENTS.md update for `{rel}`. {rationale}")
            except Exception:
                pass
        else:
            # Suggest mode: leave a detailed comment per file
            try:
                post_pr_comment(comment)
            except Exception:
                pass

        report.append({"file": rel, "changed": True, "summary": rationale})

    # Write a machine-readable report for the workflow to inspect
    (root / ".agents_update_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    if any_applied:
        # Signal to workflow that there are changes to commit
        (root / ".agents_updates_applied").write_text("1", encoding="utf-8")


if __name__ == "__main__":
    # Guard for missing keys
    for key in ["REPO", "PR_NUMBER", "GITHUB_TOKEN", "OPENAI_API_KEY"]:
        if not os.getenv(key):
            print(f"Missing required env var: {key}", file=sys.stderr)
            sys.exit(2)
    try:
        main()
    except Exception as e:
        print(f"update_agents.py failed: {e}", file=sys.stderr)
        # Do not crash the job in suggest mode
        if MODE == "apply":
            raise
