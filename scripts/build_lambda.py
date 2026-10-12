"""Build the Lambda package in build/lambda.

Lambda runs on Linux, so the dependencies are downloaded as Linux wheels
even when this script runs on Windows or macOS.

Usage: python scripts/build_lambda.py
"""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD_DIR = ROOT / "build" / "lambda"
REQUIREMENTS = ROOT / "agent" / "requirements.txt"
PYTHON_VERSION = "3.13"


def install_command():
    if shutil.which("uv"):
        return [
            "uv", "pip", "install",
            "--python-platform", "x86_64-manylinux2014",
            "--python-version", PYTHON_VERSION,
        ]
    return [
        sys.executable, "-m", "pip", "install",
        "--platform", "manylinux2014_x86_64",
        "--implementation", "cp",
        "--python-version", PYTHON_VERSION,
        "--only-binary=:all:",
    ]


def main():
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir(parents=True)

    command = install_command() + ["--target", str(BUILD_DIR), "-r", str(REQUIREMENTS)]
    subprocess.run(command, check=True)

    shutil.copytree(
        ROOT / "agent",
        BUILD_DIR / "agent",
        ignore=shutil.ignore_patterns("__pycache__", "requirements.txt"),
    )
    print(f"Lambda package is ready in {BUILD_DIR}")


if __name__ == "__main__":
    main()
