import csv
import json

import pandas as pd
import pytest

from shiftwatch.cli import main, read_csv


@pytest.mark.parametrize("gate", [[], ["--fail-on-alert"]])
def test_stdout_is_valid_json_and_never_creates_a_dash_file(tmp_path, monkeypatch, capsys, gate):
    monkeypatch.chdir(tmp_path)
    pd.DataFrame({"value": range(100)}).to_csv("ref.csv", index=False)
    pd.DataFrame({"value": range(1000, 1100)}).to_csv("current.csv", index=False)
    status = main(["compare", "ref.csv", "current.csv", "--output", "-", *gate])
    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert report["scenarios"][0]["drift"]["alert_count"] == 1
    assert status == (2 if gate else 0)
    assert captured.err == ""
    assert sorted(path.name for path in tmp_path.iterdir()) == ["current.csv", "ref.csv"]


def test_stdout_validation_error_emits_no_partial_report(tmp_path, capsys):
    source = tmp_path / "bad.csv"
    source.write_text("x,x\n1,2\n")
    with pytest.raises(SystemExit):
        main(["compare", str(source), str(source), "--output", "-"])
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Duplicate CSV headers" in captured.err


@pytest.mark.parametrize("observed,expected_status", [(0, 2), (4, 2), (5, 0)])
def test_optional_insufficient_data_gate_saves_diagnostics(tmp_path, observed, expected_status):
    source, output = tmp_path / "source.csv", tmp_path / "report.json"
    pd.DataFrame({"value": [1.0] * observed + [float("nan")] * (10 - observed)}).to_csv(
        source, index=False
    )
    common = ["compare", str(source), str(source), "--output", str(output), "--fail-on-alert"]
    assert main(common) == 0
    assert main([*common, "--fail-on-insufficient-data"]) == expected_status
    drift = json.loads(output.read_text())["scenarios"][0]["drift"]
    assert drift["alert_count"] == 0
    assert drift["features"][0]["insufficient_data"] is (observed < 5)


def test_custom_cli_drift_settings_control_quality_alerts(tmp_path):
    ref, cur, out = [tmp_path / p for p in ["ref.csv", "cur.csv", "report.json"]]
    pd.DataFrame({"value": [1.0] * 20}).to_csv(ref, index=False)
    pd.DataFrame({"value": [float("nan")] * 2 + [1.0] * 18}).to_csv(cur, index=False)
    common = ["compare", str(ref), str(cur), "--output", str(out), "--fail-on-alert"]
    assert main(common) == 2
    assert main([*common, "--missing-threshold", "0.2", "--bins", "4"]) == 0
    drift = json.loads(out.read_text())["scenarios"][0]["drift"]
    assert drift["config"]["bins"] == 4
    assert drift["config"]["missing_threshold"] == 0.2
    assert not drift["features"][0]["quality_alert"]


@pytest.mark.parametrize(
    "option,value",
    [
        ("--bins", "1"),
        ("--bins", "51"),
        ("--bins", "2.5"),
        ("--missing-threshold", "0"),
        ("--missing-threshold", "1.1"),
        ("--missing-threshold", "nan"),
    ],
)
def test_invalid_cli_drift_settings_preserve_output(tmp_path, option, value):
    source, output = tmp_path / "source.csv", tmp_path / "report.json"
    pd.DataFrame({"value": range(10)}).to_csv(source, index=False)
    output.write_text("previous report")
    with pytest.raises(SystemExit) as exc:
        main(["compare", str(source), str(source), "--output", str(output), option, value])
    assert exc.value.code == 2
    assert output.read_text() == "previous report"


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


@pytest.mark.parametrize("prefix", ["", "\ufeff\n \t\n"])
@pytest.mark.parametrize(
    "rows",
    [
        "1,10,20\n" * 5,
        "1,10,20,30\n" * 5,
        "1,10\n" + "2,20,30\n" * 4,
    ],
    ids=["implicit-index", "implicit-multi-index", "later-extra-field"],
)
def test_extra_csv_fields_rejected_without_replacing_report(tmp_path, capsys, prefix, rows):
    source = tmp_path / "wide.csv"
    source.write_text(prefix + "x,y\n" + rows, encoding="utf-8")
    output = tmp_path / "report.json"
    output.write_text("previous report")
    with pytest.raises(SystemExit) as exc:
        main(["compare", str(source), str(source), "--output", str(output)])
    assert exc.value.code == 2
    assert "CSV" in capsys.readouterr().err
    assert output.read_text() == "previous report"


def test_csv_explicit_missing_values_are_preserved(tmp_path):
    source = tmp_path / "missing.csv"
    source.write_text('"x,value",y\n1,10\n2,\n3,30\n4,40\n5,50\n')
    data = read_csv(source)
    assert data.columns.tolist() == ["x,value", "y"]
    assert data["x,value"].tolist() == [1, 2, 3, 4, 5]
    assert data["y"].isna().tolist() == [False, True, False, False, False]


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
