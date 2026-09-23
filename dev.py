"""Run backend (6767) and frontend (7890) together: python dev.py"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND_PORT = "6767"
BACKEND_HOST = "0.0.0.0"


def find_backend_python(root: Path) -> Path:
    for rel in (
        Path(".venv") / "Scripts" / "python.exe",
        Path(".venv") / "bin" / "python",
    ):
        candidate = root / rel
        if candidate.exists():
            return candidate
    return Path(sys.executable)


def backend_command(python: Path, root: Path) -> tuple[list[str], Path]:
    cmd = [
        str(python),
        "-m",
        "uvicorn",
        "app.main:app",
        "--reload",
        "--reload-dir",
        "app",
        "--host",
        BACKEND_HOST,
        "--port",
        BACKEND_PORT,
    ]
    return cmd, root


def frontend_command(root: Path) -> tuple[list[str], Path]:
    npm = shutil.which("npm") or "npm"
    cmd = [npm, "run", "dev", "--", "--host"]
    return cmd, root / "portal-admin-frontend"


def _popen(cmd: list[str], cwd: Path) -> subprocess.Popen:
    kwargs: dict = {"cwd": str(cwd)}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    return subprocess.Popen(cmd, **kwargs)


def main() -> int:
    python = find_backend_python(ROOT)
    backend_cmd, backend_cwd = backend_command(python, ROOT)
    frontend_cmd, frontend_cwd = frontend_command(ROOT)

    print(f"[dev] backend  -> {' '.join(backend_cmd)}", flush=True)
    print(f"[dev] frontend -> {' '.join(frontend_cmd)}", flush=True)

    procs: list[subprocess.Popen] = []
    try:
        procs.append(_popen(backend_cmd, backend_cwd))
        procs.append(_popen(frontend_cmd, frontend_cwd))
        while all(p.poll() is None for p in procs):
            time.sleep(0.5)
        for p in procs:
            if p.poll() is not None:
                raise SystemExit(p.returncode or 0)
    except KeyboardInterrupt:
        print("\n[dev] shutting down...", flush=True)
        return 0
    finally:
        for p in procs:
            if p.poll() is None:
                p.terminate()
        for p in procs:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()


if __name__ == "__main__":
    sys.exit(main())
