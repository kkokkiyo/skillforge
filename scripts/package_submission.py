"""Build a reviewable source bundle without local credentials, DBs or runtimes."""

import hashlib, json, os, zipfile
from pathlib import Path
from backend.config import ROOT, load_env

load_env()
out = ROOT / "submission"
out.mkdir(exist_ok=True)
base_files = [
    "README.md",
    "SECURITY.md",
    "AGENTS.md",
    "pyproject.toml",
    "requirements-lock.txt",
    ".gitignore",
    ".env.example",
    "setup_runtime.py",
    "run_live_evaluation.py",
]
folders = [
    "backend",
    "configs",
    ".kiro",
    "tests",
    "scripts",
    "docs",
    "web/src",
    "web/dist",
]
PRIVATE_FILES = {'docs/reviews/skill-api-gate.md', 'docs/09-submission-runbook.md', 'docs/07-implementation-prompts.md', 'docs/05-submission-and-pitch.md', 'docs/10-developer-handoff.md', 'docs/11-review-protocol.md'}
files = [ROOT / x for x in base_files if (ROOT / x).is_file()]
for folder in folders:
    for path in (ROOT / folder).rglob("*"):
        if (
            not path.is_file()
            or "__pycache__" in path.parts
            or path.suffix in {".pyc", ".sqlite3", ".db"}
        ):
            continue
        if path.name == "source-original.txt" or path.relative_to(ROOT).as_posix() in PRIVATE_FILES:
            continue
        files.append(path)
for name in [
    "package.json",
    "pnpm-lock.yaml",
    "pnpm-workspace.yaml",
    "tsconfig.json",
    "index.html",
]:
    path = ROOT / "web" / name
    if path.exists():
        files.append(path)
for path in (ROOT / "output/pdf").glob("*.pdf"):
    files.append(path)
for path in (ROOT / "output/video").glob("*"):
    if path.is_file() and path.suffix in {".mp4", ".json"}:
        files.append(path)
for name in [
    "live-evidence.json",
    "nat-live-evidence.json",
    "nat-span-evidence.json",
    "mcp-evidence.json",
    "korean-intent-evidence.json",
    "evidence-integrity.json",
    "workflow-evidence.json",
    "reproduction-evidence.json",
    "safety-matrix.json",
    "policy-change-evidence.json",
    "policy-change-live-retry.json",
]:
    path = ROOT / "artifacts" / name
    if path.exists():
        files.append(path)
for eid in ["eval-1fbaadfc4c465a19", "eval-dc5a773edccd641d"]:
    for path in (ROOT / "artifacts/eval" / eid).glob("*"):
        if path.is_file() and path.suffix in {".json", ".jsonl", ".md"}:
            files.append(path)
secrets = [
    v.encode()
    for k in ["NVIDIA_API_KEY", "SKILLFORGE_OPERATOR_SESSION"]
    if (v := os.getenv(k, "")) and len(v) > 12
]
manifest = {}
for path in sorted(set(files)):
    data = path.read_bytes()
    if any(secret in data for secret in secrets):
        raise SystemExit(
            "Secret found in candidate file: " + str(path.relative_to(ROOT))
        )
    manifest[str(path.relative_to(ROOT))] = hashlib.sha256(data).hexdigest()
manifest_path = ROOT / "artifacts/public-source-manifest.json"
manifest_path.parent.mkdir(parents=True, exist_ok=True)
manifest_path.write_text(
    json.dumps(
        {
            "files": manifest,
            "scope": "source + built UI + selected synthetic evidence",
            "repository_url": "https://github.com/kkokkiyo/skillforge",
            "team_name": "TraceMakers",
        },
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)
archive = out / "SkillForge-review-bundle.zip"
with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
    for path in sorted(set(files)):
        z.write(path, "skillforge/" + str(path.relative_to(ROOT)))
    z.write(manifest_path, "skillforge/artifacts/public-source-manifest.json")
print(
    json.dumps(
        {
            "bundle": str(archive),
            "files": len(manifest),
            "bytes": archive.stat().st_size,
            "credential_scan": "passed",
        }
    )
)
