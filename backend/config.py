"""Load explicitly project-local environment without printing secrets."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_env():
    for name in (".env.local", ".enc.API", ".env.API", ".env"):
        path = ROOT / name
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip().removeprefix("export ")
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if key in {
                "NVIDIA_API_KEY",
                "NVIDIA_MODEL",
                "SKILLFORGE_OPERATOR_SESSION",
                "PORT",
                "SKILLFORGE_DB",
                "NVIDIA_MIN_INTERVAL",
            }:
                value = value.strip().strip("\"'")
                if value and not os.environ.get(key):
                    os.environ[key] = value
