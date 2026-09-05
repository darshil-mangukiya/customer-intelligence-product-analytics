from __future__ import annotations

import argparse
import subprocess
import sys


def _run(command: list[str]) -> None:
    print(f"\n$ {' '.join(command)}")
    subprocess.run(command, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a one-command local demo build.")
    parser.add_argument("--skip-pipeline", action="store_true", help="Only print demo launch instructions.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.skip_pipeline:
        _run(
            [
                sys.executable,
                "-m",
                "etl.run_pipeline",
                "--customers",
                "2500",
                "--products",
                "150",
                "--orders",
                "12000",
                "--sessions",
                "9000",
                "--seed",
                "42",
            ]
        )
        _run([sys.executable, "-m", "orchestration.dag_runner", "--downstream-only"])
        _run([sys.executable, "-m", "pytest"])

    print(
        """
Demo build is ready.

Launch options:
  make api        # http://127.0.0.1:8000/docs
  make app        # http://127.0.0.1:8501
"""
    )


if __name__ == "__main__":
    main()
