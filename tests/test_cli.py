import json

import pandas as pd
import pytest

from shiftwatch.cli import main


def test_compare_writes_portable_report_and_returns_ci_failure(tmp_path):
    ref, cur, out = [tmp_path / p for p in ["ref.csv", "current.csv", "nested/report.json"]]
    pd.DataFrame({"value": range(100)}).to_csv(ref, index=False)
    pd.DataFrame({"value": range(1000, 1100)}).to_csv(cur, index=False)
    result = main(["compare", str(ref), str(cur), "--output", str(out), "--fail-on-alert"])
    assert result == 2
    report = json.loads(out.read_text())
    assert report["schema_version"] == "shiftwatch/v1"
    assert report["scenarios"][0]["metrics"] is None
    assert report["scenarios"][0]["drift"]["alert_count"] == 1


def test_duplicate_csv_headers_rejected(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("x,x\n" + "1,2\n" * 10)
    with pytest.raises(SystemExit) as exc:
        main(["compare", str(path), str(path)])
    assert exc.value.code == 2
