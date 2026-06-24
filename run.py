"""Single entry point for EasyTravel.

Usage (from inside the easytravel/ folder):
    python run.py

This will:
  1. Generate the sample transcripts Excel (if missing).
  2. Start the FastAPI backend on port 8002 as a child process.
  3. Wait until the backend's /health endpoint responds before launching the UI.
  4. Start the Streamlit frontend on port 8502 in the foreground.
  5. On Ctrl+C or exit, kill the backend's process tree so its port is released.
"""
from __future__ import annotations
from pathlib import Path
import atexit
import subprocess
import sys
import time
import urllib.error
import urllib.request

BASE_DIR = Path(__file__).resolve().parent
SAMPLE_DIR = BASE_DIR / "sample_data"
EXCEL_MARKER = SAMPLE_DIR / "EasyTravel_Sample_Transcripts.xlsx"

BACKEND_PORT = 8002
FRONTEND_PORT = 8502
BACKEND_HEALTH_URL = f"http://127.0.0.1:{BACKEND_PORT}/health"
BACKEND_STARTUP_TIMEOUT = 60

IS_WINDOWS = sys.platform.startswith("win")

_backend_proc: subprocess.Popen | None = None


def _terminate_backend():
    global _backend_proc
    proc = _backend_proc
    _backend_proc = None
    if not proc or proc.poll() is not None:
        return
    if IS_WINDOWS:
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
            )
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
    else:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


def _start_backend() -> subprocess.Popen:
    return subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn",
            "backend:app",
            "--port", str(BACKEND_PORT),
            "--reload",
        ],
        cwd=str(BASE_DIR),
    )


def _wait_for_backend() -> bool:
    deadline = time.time() + BACKEND_STARTUP_TIMEOUT
    while time.time() < deadline:
        if _backend_proc and _backend_proc.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(BACKEND_HEALTH_URL, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, ConnectionError, TimeoutError, OSError):
            pass
        time.sleep(1)
    return False


def _run_frontend():
    subprocess.run(
        [
            sys.executable, "-m", "streamlit", "run",
            str(BASE_DIR / "app.py"),
            "--server.port", str(FRONTEND_PORT),
            "--server.headless", "false",
        ],
        cwd=str(BASE_DIR),
    )


def main():
    global _backend_proc
    print("=" * 60)
    print("  EasyTravel - AI Assurance Workshop App")
    print("=" * 60)

    if not EXCEL_MARKER.exists():
        print("\n[1/2] Generating sample transcripts Excel...")
        result = subprocess.run([sys.executable, str(BASE_DIR / "generate_excel.py")], cwd=str(BASE_DIR))
        if result.returncode != 0:
            print("Excel generation failed. See errors above. Exiting.")
            sys.exit(1)
    else:
        print("\n[1/2] Sample Excel already exists, skipping.")

    print(f"\n[2/2] Starting backend (port {BACKEND_PORT})...")
    atexit.register(_terminate_backend)
    _backend_proc = _start_backend()

    print("      waiting for backend to become healthy...")
    if not _wait_for_backend():
        print("\nBackend failed to start within the timeout window.")
        print(f"Check that port {BACKEND_PORT} is free and that dependencies are installed.")
        _terminate_backend()
        sys.exit(1)
    print("      backend ready.")

    print(f"\n>>> Open your browser at: http://localhost:{FRONTEND_PORT}")
    print(">>> Press Ctrl+C in this window to stop\n")

    try:
        _run_frontend()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        _terminate_backend()


if __name__ == "__main__":
    main()
