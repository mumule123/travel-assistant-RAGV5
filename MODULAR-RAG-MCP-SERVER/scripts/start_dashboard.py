"""Convenience launcher for the Modular RAG Dashboard.

Usage::

    python scripts/start_dashboard.py
    python scripts/start_dashboard.py --port 8502
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the Modular RAG Dashboard")
    parser.add_argument("--port", type=int, default=8502, help="Port to serve the dashboard on")
    parser.add_argument("--host", type=str, default="localhost", help="Host to bind to")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    app_path = project_root / "src" / "observability" / "dashboard" / "app.py"
    if not app_path.exists():
        print(f"Error: Dashboard app not found at {app_path}")
        sys.exit(1)

    # 注入 PYTHONPATH，让 streamlit 运行时能找到 src 目录
    import os
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root) + (f":{env['PYTHONPATH']}" if "PYTHONPATH" in env else "")

    cmd = [
        sys.executable, "-m", "streamlit", "run",
        str(app_path),
        "--server.port", str(args.port),
        "--server.address", args.host,
    ]
    print(f"Starting Dashboard: {' '.join(cmd)}")
    subprocess.run(cmd, env=env)


if __name__ == "__main__":
    main()
