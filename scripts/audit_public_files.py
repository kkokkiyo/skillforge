"""Scan the exact publication manifest without printing credential values."""
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    "nvidia_key": rb"nvapi-[A-Za-z0-9_-]{20,}",
    "github_token": rb"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})",
    "private_key": rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    "personal_email": rb"[A-Za-z0-9._%+-]+@(?:gmail|naver|daum|hotmail|outlook)\.(?:com|net)",
    "mobile_phone": rb"(?<!\d)01[016789][- ]?\d{3,4}[- ]?\d{4}(?!\d)",
}


def audit():
    secrets = set()
    for key in ("NVIDIA_API_KEY", "SKILLFORGE_OPERATOR_SESSION"):
        value = os.getenv(key, "")
        if len(value) > 12:
            secrets.add(value.encode())
    for name in (".env", ".env.API", ".enc.API", ".env.local"):
        path = ROOT / name
        if path.is_file():
            for line in path.read_text().splitlines():
                if "=" in line:
                    key, value = line.split("=", 1)
                    if key.strip() in {"NVIDIA_API_KEY", "SKILLFORGE_OPERATOR_SESSION"}:
                        value = value.strip().strip("\"'")
                        if len(value) > 12:
                            secrets.add(value.encode())
    manifest = json.loads((ROOT / "artifacts/public-source-manifest.json").read_text())
    findings = []
    def scan(label, data):
        for name, pattern in PATTERNS.items():
            if re.search(pattern, data):
                findings.append({"file": label, "rule": name})
        if any(secret in data for secret in secrets):
            findings.append({"file": label, "rule": "exact_local_credential"})
    for name, expected in manifest["files"].items():
        path = ROOT / name
        if not path.resolve().is_relative_to(ROOT.resolve()):
            raise ValueError("Manifest path outside project")
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            findings.append({"file": name, "rule": "manifest_hash_mismatch"})
        if path.name in {".env", ".env.API", ".enc.API", ".env.local", "source-original.txt"} or path.suffix in {".db", ".sqlite3"}:
            findings.append({"file": name, "rule": "private_file"})
        scan(name, data)
    git_blobs = 0
    if (ROOT / ".git").is_dir():
        objects = subprocess.check_output(["git", "rev-list", "--objects", "--all"], cwd=ROOT).decode().splitlines()
        for entry in objects:
            oid, _, label = entry.partition(" ")
            kind = subprocess.check_output(["git", "cat-file", "-t", oid], cwd=ROOT).strip()
            if kind == b"blob":
                git_blobs += 1
                scan("history:" + label, subprocess.check_output(["git", "cat-file", "blob", oid], cwd=ROOT))
    result = {"passed": not findings, "files": len(manifest["files"]), "history_blobs": git_blobs, "local_credentials_available": bool(secrets), "findings": findings}
    print(json.dumps(result))
    return result


if __name__ == "__main__":
    raise SystemExit(0 if audit()["passed"] else 1)
