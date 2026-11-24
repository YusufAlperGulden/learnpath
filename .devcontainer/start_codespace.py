"""Starts PostgreSQL 16, FastAPI (migrated + seeded), and Vite automatically inside Codespaces."""

from __future__ import annotations

import shutil
import socket
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


def main() -> None:
    env_file = REPO_ROOT / ".env"
    env_example = REPO_ROOT / ".env.example"
    if not env_file.exists() and env_example.exists():
        shutil.copyfile(env_example, env_file)

    # 1. Start PostgreSQL 16 container
    subprocess.run(["docker", "compose", "up", "-d"], cwd=str(REPO_ROOT), check=True)

    # 2. Launch FastAPI backend (runs alembic upgrade head + seeds on startup) if not running
    if not _port_open(8000):
        backend_log = open("/tmp/learnpath-backend.log", "ab")  # noqa: SIM115
        subprocess.Popen(
            [sys.executable, "-m", "scripts.start_server"],
            cwd=str(REPO_ROOT / "backend"),
            stdout=backend_log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

    # 3. Launch Vite frontend dev server on :5173 if not running
    if not _port_open(5173):
        frontend_log = open("/tmp/learnpath-frontend.log", "ab")  # noqa: SIM115
        subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=str(REPO_ROOT / "frontend"),
            stdout=frontend_log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

    print("LearnPath Codespace services launched! Port 5173 will open automatically.")


if __name__ == "__main__":
    main()
