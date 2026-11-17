"""One-shot setup: create .venv, install the project, then run the guided setup.

Usage (from the repository folder):
    python scripts/bootstrap.py            # everything (capture + analysis)
    python scripts/bootstrap.py --core     # analysis only (no yt-dlp / whisper)

Only the Python standard library is used here.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def venv_python(env: Path) -> Path:
    return env / ("Scripts/python.exe" if sys.platform.startswith("win") else "bin/python")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--core", action="store_true", help="install only the analysis part")
    ap.add_argument("--browser", help="browser for cookies (skips the question)")
    args = ap.parse_args()

    if sys.version_info < (3, 9):
        print("Python 3.9 or newer is needed.")
        return 1
    env = ROOT / ".venv"
    if not venv_python(env).exists():
        print(f"creating {env.name} ...")
        venv.EnvBuilder(with_pip=True).create(env)
    py = str(venv_python(env))
    extra = ".[yaml,dev]" if args.core else ".[all]"
    subprocess.run([py, "-m", "pip", "install", "--upgrade", "pip"], check=True, cwd=ROOT)
    subprocess.run([py, "-m", "pip", "install", "-e", extra], check=True, cwd=ROOT)
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            print(f"NOTE: {tool} not found on PATH. Install ffmpeg: https://ffmpeg.org/download.html "
                  "(Windows: winget install Gyan.FFmpeg; macOS: brew install ffmpeg; Linux: apt install ffmpeg)")
    cmd = [py, "-m", "fuffaguru", "--root", str(ROOT), "setup"]
    if args.browser:
        cmd += ["--browser", args.browser]
    subprocess.run(cmd, check=False, cwd=ROOT)
    print(f"\nDone. Use: {Path(py).relative_to(ROOT)} -m fuffaguru --help")
    return 0


if __name__ == "__main__":
    sys.exit(main())
