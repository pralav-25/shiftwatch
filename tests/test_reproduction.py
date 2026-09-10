import json
import subprocess
import sys
from pathlib import Path

import pytest

CHECKER = Path(__file__).resolve().parents[1] / "scripts" / "check_reproduction.py"


def run_checker(tmp_path, expected, actual, optimized):
    left, right = tmp_path / "expected.json", tmp_path / "actual.json"
    left.write_text(json.dumps(expected), encoding="utf-8")
    right.write_text(json.dumps(actual), encoding="utf-8")
    flags = ["-O"] if optimized else []
    return subprocess.run(
        [sys.executable, *flags, str(CHECKER), str(left), str(right)],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize("optimized", [False, True], ids=["normal", "optimized"])
@pytest.mark.parametrize(
    ("expected", "actual", "path"),
    [
        ({"accuracy": 0.98}, {"accuracy": 0.25}, "root.accuracy"),
        ({"sha256": "original"}, {"sha256": "changed"}, "root.sha256"),
        ({"rows": 54}, {"rows": 53}, "root.rows"),
        ({"accuracy": 0.98}, {"accuracy": 0.98, "extra": True}, "root"),
        ({"features": ["a", "b"]}, {"features": ["a"]}, "root.features"),
    ],
)
def test_changed_reports_fail_in_both_python_modes(tmp_path, expected, actual, path, optimized):
    result = run_checker(tmp_path, expected, actual, optimized)
    assert result.returncode != 0
    assert "Report reproduced" not in result.stdout
    assert path in result.stderr


@pytest.mark.parametrize("optimized", [False, True], ids=["normal", "optimized"])
def test_reproduction_allows_numerical_tolerance_and_environment_changes(tmp_path, optimized):
    expected = {"accuracy": 0.98, "rows": 54, "environment": {"python": "3.12.13"}}
    actual = {"accuracy": 0.98000001, "rows": 54, "environment": {"python": "3.12.14"}}
    result = run_checker(tmp_path, expected, actual, optimized)
    assert result.returncode == 0, result.stderr
    assert "Report reproduced within numerical tolerance." in result.stdout
