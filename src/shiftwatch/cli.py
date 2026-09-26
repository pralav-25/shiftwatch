"""Portable command line interface. No network or model download is required."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import warnings
from pathlib import Path

import pandas as pd

from .drift import compare_frames
from .experiment import run_experiment


def read_csv(path: Path, *, delimiter: str = ",") -> pd.DataFrame:
    if (
        not isinstance(delimiter, str)
        or len(delimiter) != 1
        or not delimiter.isascii()
        or delimiter in '\r\n\x00"'
    ):
        raise ValueError("delimiter must be one ASCII character other than newline, NUL, or quote")
    # Read the header as literal data before pandas can rename duplicates.
    # Using the same parser honors blank lines, quoting, and UTF-8 BOMs.
    headers = (
        pd.read_csv(path, sep=delimiter, header=None, nrows=1, dtype=str, na_filter=False)
        .iloc[0]
        .tolist()
    )
    if any(name == "" for name in headers):
        raise ValueError(f"CSV headers must not be empty in {path.name}")
    if len(set(headers)) != len(headers):
        raise ValueError(f"Duplicate CSV headers in {path.name}")
    # A wider data row otherwise makes pandas infer an index, silently moving
    # leading values out of the monitored features. Disabling index inference
    # alone still truncates those rows, so treat its data-loss warning as an error.
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", pd.errors.ParserWarning)
            return pd.read_csv(path, sep=delimiter, index_col=False)
    except pd.errors.ParserWarning as exc:
        raise ValueError(
            f"Invalid CSV in {path.name}: data rows have more fields than the header. "
            "Give every column a header and check for extra delimiters."
        ) from exc
    except pd.errors.ParserError as exc:
        raise ValueError(f"Invalid CSV in {path.name}: {exc}") from exc


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
    demo.add_argument(
        "--output",
        type=Path,
        default=Path("public/reports/demo.json"),
        help="Report path, or - for JSON on standard output",
    )
    compare = commands.add_parser("compare", help="Compare two numerical feature CSV files")
    compare.add_argument("reference", type=Path)
    compare.add_argument("current", type=Path)
    compare.add_argument(
        "--delimiter", default=",", help="One ASCII field separator for both files (default: comma)"
    )
    compare.add_argument(
        "--output",
        type=Path,
        default=Path("report.json"),
        help="Report path, or - for JSON on standard output",
    )
    compare.add_argument("--alpha", type=float, default=0.05)
    compare.add_argument("--psi-threshold", type=float, default=0.2)
    compare.add_argument(
        "--missing-threshold",
        type=float,
        default=0.05,
        help="Absolute missing-rate change that raises a quality alert, in (0, 1]",
    )
    compare.add_argument(
        "--bins", type=int, default=10, help="Reference quantile bins for PSI, from 2 to 50"
    )
    compare.add_argument(
        "--fail-on-alert", action="store_true", help="Exit 2 when drift is flagged"
    )
    compare.add_argument(
        "--fail-on-insufficient-data",
        action="store_true",
        help="Exit 2 when any feature has fewer than five observed values in either CSV",
    )
    args = parser.parse_args(argv)
    to_stdout = args.output == Path("-")
    try:
        if args.command == "demo":
            report = run_experiment(args.seed)
        else:
            for source in (args.reference, args.current):
                if not to_stdout and (
                    args.output.resolve() == source.resolve()
                    or (args.output.exists() and source.exists() and args.output.samefile(source))
                ):
                    raise ValueError("Output must not overwrite an input CSV")
            result = compare_frames(
                read_csv(args.reference, delimiter=args.delimiter),
                read_csv(args.current, delimiter=args.delimiter),
                alpha=args.alpha,
                psi_threshold=args.psi_threshold,
                missing_threshold=args.missing_threshold,
                bins=args.bins,
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
        if to_stdout:
            sys.stdout.write(json.dumps(report, indent=2, allow_nan=False) + "\n")
        else:
            write_report(args.output, report)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    if not to_stdout:
        print(f"Saved {args.output}")
    if args.command == "compare" and args.fail_on_alert and result["alert_count"]:
        return 2
    if (
        args.command == "compare"
        and args.fail_on_insufficient_data
        and any(feature["insufficient_data"] for feature in result["features"])
    ):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
