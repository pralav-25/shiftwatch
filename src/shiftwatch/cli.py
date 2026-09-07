"""Portable command line interface. No network or model download is required."""

from __future__ import annotations

import argparse
import csv
import json
import os
import tempfile
from pathlib import Path

import pandas as pd

from .drift import compare_frames
from .experiment import run_experiment


def read_csv(path: Path) -> pd.DataFrame:
    with path.open(newline="", encoding="utf-8-sig") as file:
        headers = next(csv.reader(file), [])
    if len(set(headers)) != len(headers):
        raise ValueError(f"Duplicate CSV headers in {path.name}")
    return pd.read_csv(path)


def write_report(path: Path, report: dict) -> None:
    """Replace a report only after its complete JSON has been written successfully."""
    serialized = json.dumps(report, indent=2, allow_nan=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as file:
            temporary = Path(file.name)
            file.write(serialized)
            file.flush()
            os.fsync(file.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Train, evaluate, and monitor numerical data drift."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo", help="Reproduce the Wine classification experiment")
    demo.add_argument("--seed", type=int, default=42)
    demo.add_argument("--output", type=Path, default=Path("public/reports/demo.json"))
    compare = commands.add_parser("compare", help="Compare two numerical feature CSV files")
    compare.add_argument("reference", type=Path)
    compare.add_argument("current", type=Path)
    compare.add_argument("--output", type=Path, default=Path("report.json"))
    compare.add_argument("--alpha", type=float, default=0.05)
    compare.add_argument("--psi-threshold", type=float, default=0.2)
    compare.add_argument(
        "--fail-on-alert", action="store_true", help="Exit 2 when drift is flagged"
    )
    args = parser.parse_args(argv)
    try:
        if args.command == "demo":
            report = run_experiment(args.seed)
        else:
            for source in (args.reference, args.current):
                if args.output.resolve() == source.resolve() or (
                    args.output.exists() and source.exists() and args.output.samefile(source)
                ):
                    raise ValueError("Output must not overwrite an input CSV")
            result = compare_frames(
                read_csv(args.reference),
                read_csv(args.current),
                alpha=args.alpha,
                psi_threshold=args.psi_threshold,
            )
            report = {
                "schema_version": "shiftwatch/v1",
                "kind": "comparison",
                "seed": None,
                "dataset": {
                    "name": args.current.stem,
                    "rows": result["current_rows"],
                    "features": result["feature_count"],
                    "classes": None,
                },
                "selected_model": None,
                "models": [],
                "scenarios": [
                    {
                        "id": "custom",
                        "name": "CSV comparison",
                        "description": f"{args.reference.name} → {args.current.name}",
                        "synthetic": False,
                        "drift": result,
                        "metrics": None,
                    }
                ],
            }
        write_report(args.output, report)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(f"Saved {args.output}")
    if args.command == "compare" and args.fail_on_alert and result["alert_count"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
