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


def test_output_cannot_overwrite_input_csv(tmp_path):
    source = tmp_path / "input.csv"
    content = "value\n1\n2\n3\n4\n5\n"
    source.write_text(content)
    with pytest.raises(SystemExit):
        main(["compare", str(source), str(source), "--output", str(source)])
    assert source.read_text() == content


def test_failed_replacement_preserves_previous_report(tmp_path, monkeypatch):
    from pathlib import Path

    from shiftwatch.cli import write_report

    output = tmp_path / "report.json"
    output.write_text('{"previous": true}\n')

    def fail(*args):
        raise OSError("Disk unavailable")

    monkeypatch.setattr(Path, "replace", fail)
    with pytest.raises(OSError, match="Disk unavailable"):
        write_report(output, {"new": True})
    assert json.loads(output.read_text()) == {"previous": True}
    assert list(tmp_path.iterdir()) == [output]


def test_invalid_json_preserves_previous_report(tmp_path):
    from shiftwatch.cli import write_report

    output = tmp_path / "report.json"
    output.write_text("previous")
    with pytest.raises(ValueError):
        write_report(output, {"value": float("nan")})
    assert output.read_text() == "previous"


def test_atomic_report_supports_unicode_and_nested_paths(tmp_path):
    from shiftwatch.cli import write_report

    output = tmp_path / "nested" / "report.json"
    write_report(output, {"name": "Données"})
    assert json.loads(output.read_text(encoding="utf-8")) == {"name": "Données"}


@pytest.mark.parametrize("alias_type", ["symlink", "hardlink"])
def test_output_alias_cannot_overwrite_input(tmp_path, alias_type):
    source = tmp_path / "input.csv"
    alias = tmp_path / "output.json"
    content = "value\n1\n2\n3\n4\n5\n"
    source.write_text(content)
    if alias_type == "symlink":
        alias.symlink_to(source)
    else:
        alias.hardlink_to(source)
    with pytest.raises(SystemExit):
        main(["compare", str(source), str(source), "--output", str(alias)])
    assert source.read_text() == content
