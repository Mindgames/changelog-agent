import os, re, json, sys, pathlib, requests

REPO = os.environ["REPO"]               # e.g., org/name
OWNER, NAME = REPO.split("/")
PR_NUMBER = int(os.environ["PR_NUMBER"])
GH_API = "https://api.github.com"
GH_HEADERS = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
}

def gh_get(url, params=None):
    r = requests.get(url, headers=GH_HEADERS, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

# ---- Fetch PR context --------------------------------------------------------
pr = gh_get(f"{GH_API}/repos/{OWNER}/{NAME}/pulls/{PR_NUMBER}")
files = gh_get(f"{GH_API}/repos/{OWNER}/{NAME}/pulls/{PR_NUMBER}/files")
labels = [lbl["name"] for lbl in pr.get("labels", [])]
author = pr["user"]["login"]
title = pr["title"]
body = pr.get("body") or ""
changed = [f["filename"] for f in files]
top_dirs = [p.split("/")[0] for p in changed if "/" in p]
scope_guess = max(set(top_dirs), key=top_dirs.count) if top_dirs else ""

def summarize_files(fs, cap=25):
    out = []
    for f in fs[:cap]:
        out.append(f"{f['status']} {f['filename']} (+{f['additions']}/-{f['deletions']})")
    if len(fs) > cap:
        out.append(f"... and {len(fs)-cap} more")
    return "\n".join(out)

diff_summary = summarize_files(files)

# ---- LLM call (OpenAI Responses API) ----------------------------------------
from openai import OpenAI

client = OpenAI(
    base_url=os.getenv("OPENAI_BASE_URL"),
    api_key=os.environ["OPENAI_API_KEY"],
)

model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

schema = {
    "name": "ChangelogEntry",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "category": {"type": "string", "enum": ["Added","Changed","Fixed","Deprecated","Removed","Security"]},
            "summary": {"type": "string", "maxLength": 240},
            "scope": {"type": "string"},
            "breaking": {"type": "boolean"},
            "migration": {"type": "string"},
            "references": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["category", "summary", "breaking", "references"],
        "additionalProperties": False
    }
}

prompt = f"""You are writing ONE bullet for a CHANGELOG in Keep a Changelog style.

Constraints:
- One sentence, imperative mood, ≤ 20 words, no trailing period
- Audience: end users (not maintainers)
- Prefer user-visible impact over implementation detail
- If labels contain 'breaking-change' or PR body includes 'BREAKING CHANGE', set breaking=true and include a brief 'migration' string
- Category must be one of: Added, Changed, Fixed, Deprecated, Removed, Security
- If most files share a top-level directory, use it as 'scope'

Input
PR #{PR_NUMBER} by @{author}
Title: {title}
Labels: {", ".join(labels) or "(none)"}
Likely scope: {scope_guess or "(none)"}

PR body (truncated):
{body[:4000]}

Changed files (status path +/−):
{diff_summary}
"""

try:
    resp = client.responses.create(
        model=model,
        input=prompt,
        response_format={"type":"json_schema","json_schema":schema},
    )
    parsed = json.loads(resp.output_text)
except Exception:
    parsed = {
        "category": "Changed",
        "summary": title.strip()[:200],
        "scope": scope_guess,
        "breaking": False,
        "migration": "",
        "references": []
    }

refs = set(parsed.get("references", []))
refs.update({f"#{PR_NUMBER}", f"@{author}"})
parsed["references"] = sorted(refs)

# ---- Update CHANGELOG.md -----------------------------------------------------
root = pathlib.Path(os.getenv("GITHUB_WORKSPACE", "."))
chlog = root / os.getenv("CHANGELOG_PATH", "CHANGELOG.md")

if not chlog.exists():
    chlog.write_text(
        "# Changelog\n\n"
        "All notable changes to this project will be documented in this file.\n\n"
        "The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), "
        "and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).\n\n"
        "## [Unreleased]\n\n",
        encoding="utf-8",
    )

text = chlog.read_text(encoding="utf-8")

# Idempotency
if re.search(rf"(#){PR_NUMBER}\b", text):
    sys.exit(0)

def ensure_section(txt: str, header: str) -> str:
    marker = f"\n### {header}\n"
    if marker not in txt:
        txt = txt.replace("## [Unreleased]\n", f"## [Unreleased]\n\n### {header}\n\n")
    return txt

category = parsed.get("category", "Changed")
text = ensure_section(text, category)

bullet_parts = []
if parsed.get("scope"):
    bullet_parts.append(f"[{parsed['scope']}]")
if parsed.get("breaking"):
    bullet_parts.append("⚠️ BREAKING")
bullet_parts.append(parsed.get("summary",""))

bullet = " - " + " ".join(p for p in bullet_parts if p)
refs_str = " (" + ", ".join(parsed["references"]) + ")"

insertion = f"{bullet}{refs_str}\n"
if parsed.get("breaking") and parsed.get("migration"):
    insertion += f"   - **Migration:** {parsed['migration']}\n"

pattern = rf"(## \[Unreleased\][\s\S]*?### {re.escape(category)}\n)"
m = re.search(pattern, text)
if m:
    idx = m.end()
    text = text[:idx] + insertion + text[idx:]
else:
    text = text.replace("## [Unreleased]\n", f"## [Unreleased]\n\n### {category}\n{insertion}\n")

chlog.write_text(text, encoding="utf-8")
