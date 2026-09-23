"""Run backend (6767) and frontend (7890) together: python dev.py"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT / "portal-admin-frontend"
BACKEND_PORT = "6767"
BACKEND_HOST = "0.0.0.0"
FRONTEND_PORT = 7890


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


def install_command(root: Path) -> tuple[list[str], Path]:
    npm = shutil.which("npm") or "npm"
    cmd = [npm, "install"]
    return cmd, root / "portal-admin-frontend"


def run_blocking(cmd: list[str], cwd: Path) -> int:
    try:
        return subprocess.call(cmd, cwd=str(cwd))
    except OSError as e:
        print(f"[dev] failed to run {' '.join(cmd)}: {e}", flush=True)
        return 1


def ensure_frontend_deps(root: Path) -> bool:
    node_modules = root / "portal-admin-frontend" / "node_modules"
    if node_modules.exists():
        return True
    print("[dev] node_modules missing — running npm install...", flush=True)
    cmd, cwd = install_command(root)
    return run_blocking(cmd, cwd) == 0


def wait_until_listening(host: str, port: int, timeout: float = 30.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def _popen(cmd: list[str], cwd: Path) -> subprocess.Popen:
    kwargs: dict = {"cwd": str(cwd)}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    return subprocess.Popen(cmd, **kwargs)


def main() -> int:
    if not ensure_frontend_deps(ROOT):
        print("[dev] npm install failed — aborting.", flush=True)
        return 1

    python = find_backend_python(ROOT)
    backend_cmd, backend_cwd = backend_command(python, ROOT)
    frontend_cmd, frontend_cwd = frontend_command(ROOT)

    print(f"[dev] backend  -> {' '.join(backend_cmd)}", flush=True)
    print(f"[dev] frontend -> {' '.join(frontend_cmd)}", flush=True)

    procs: list[tuple[str, subprocess.Popen]] = []
    try:
        procs.append(("backend", _popen(backend_cmd, backend_cwd)))
        procs.append(("frontend", _popen(frontend_cmd, frontend_cwd)))

        if not wait_until_listening("127.0.0.1", int(BACKEND_PORT), timeout=30):
            print("[dev] backend did not start listening on 6767", flush=True)
            return 1
        if not wait_until_listening("127.0.0.1", FRONTEND_PORT, timeout=30):
            print("[dev] frontend did not start listening on 7890", flush=True)
            return 1

        print(f"[dev] ready  UI  -> http://localhost:{FRONTEND_PORT}/", flush=True)
        print(f"[dev] ready  API  -> http://localhost:{BACKEND_PORT}/docs", flush=True)

        while all(p.poll() is None for _, p in procs):
            time.sleep(0.5)
        for name, p in procs:
            if p.poll() is not None:
                code = p.returncode or 0
                print(f"[dev] {name} exited with code {code}", flush=True)
                raise SystemExit(code)
    except KeyboardInterrupt:
        print("\n[dev] shutting down...", flush=True)
        return 0
    finally:
        for _, p in procs:
            if p.poll() is None:
                p.terminate()
        for _, p in procs:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()


if __name__ == "__main__":
    sys.exit(main())
