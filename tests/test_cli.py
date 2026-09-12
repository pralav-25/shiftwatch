import csv
import json

import pandas as pd
import pytest

from shiftwatch.cli import main, read_csv


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


@pytest.mark.parametrize("missing_counts", [(5, 6), (6, 5)])
def test_fail_on_alert_includes_exact_missingness_boundary(tmp_path, missing_counts):
    ref, cur, out = [tmp_path / p for p in ["ref.csv", "current.csv", "report.json"]]
    for path, missing in zip([ref, cur], missing_counts, strict=True):
        pd.DataFrame({"value": [float("nan")] * missing + [1.0] * (20 - missing)}).to_csv(
            path, index=False
        )
    result = main(["compare", str(ref), str(cur), "--output", str(out), "--fail-on-alert"])
    assert result == 2
    drift = json.loads(out.read_text())["scenarios"][0]["drift"]
    assert drift["alert_count"] == 1
    assert drift["features"][0]["quality_alert"]
    assert not drift["features"][0]["distribution_alert"]


@pytest.mark.parametrize("prefix", ["", "\n", "\r\n \t\r\n", "\ufeff\n"])
def test_duplicate_csv_headers_rejected(tmp_path, capsys, prefix):
    path = tmp_path / "bad.csv"
    path.write_text(prefix + "x,x\n" + "1,2\n" * 10, encoding="utf-8")
    output = tmp_path / "report.json"
    output.write_text("previous report")
    with pytest.raises(SystemExit) as exc:
        main(["compare", str(path), str(path), "--output", str(output)])
    assert exc.value.code == 2
    assert "Duplicate CSV headers in bad.csv" in capsys.readouterr().err
    assert output.read_text() == "previous report"


@pytest.mark.parametrize(
    "headers",
    [["x", "x.1"], ["NA", "NaN"], ["01", "1"], ["sensor,value", "x"], ["   "]],
)
def test_header_validation_preserves_distinct_literal_names(tmp_path, headers):
    path = tmp_path / "valid.csv"
    expected = pd.DataFrame({name: range(10) for name in headers})
    path.write_text(
        "\ufeff\n \t\n" + expected.to_csv(index=False, quoting=csv.QUOTE_ALL), encoding="utf-8"
    )
    pd.testing.assert_frame_equal(read_csv(path), expected)


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
