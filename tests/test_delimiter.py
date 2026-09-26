import json

import pandas as pd
import pytest

from shiftwatch.cli import main, read_csv


@pytest.mark.parametrize("delimiter", [";", "\t", "|"])
def test_noncomma_csv_roundtrip_and_cli_report(tmp_path, delimiter):
    source, output = tmp_path / "source.csv", tmp_path / "report.json"
    expected = pd.DataFrame({f"quoted{delimiter}name": range(10), "other": range(10, 20)})
    expected.to_csv(source, sep=delimiter, index=False)
    pd.testing.assert_frame_equal(read_csv(source, delimiter=delimiter), expected)
    assert (
        main(
            ["compare", str(source), str(source), "--delimiter", delimiter, "--output", str(output)]
        )
        == 0
    )
    drift = json.loads(output.read_text())["scenarios"][0]["drift"]
    assert drift["feature_count"] == 2 and drift["alert_count"] == 0
    assert [f["name"] for f in drift["features"]] == list(expected.columns)


@pytest.mark.parametrize("delimiter", ["", "::", "\n", "\r", '"', "é", "\x00", None])
def test_invalid_delimiter_rejected_before_opening_file(tmp_path, delimiter):
    with pytest.raises(ValueError, match="delimiter"):
        read_csv(tmp_path / "does-not-exist.csv", delimiter=delimiter)


@pytest.mark.parametrize("content", ["x;x\n1;2\n", ";y\n1;2\n", "x;y\n1;2;3\n"])
def test_header_and_width_guards_apply_to_custom_delimiters(tmp_path, capsys, content):
    source, output = tmp_path / "bad.csv", tmp_path / "report.json"
    source.write_text(content)
    output.write_text("previous")
    with pytest.raises(SystemExit) as exc:
        main(["compare", str(source), str(source), "--delimiter", ";", "--output", str(output)])
    assert exc.value.code == 2
    assert "CSV" in capsys.readouterr().err
    assert output.read_text() == "previous"
