import json

import pandas as pd
import pytest

from shiftwatch.cli import main, read_csv


def test_extra_markers_preserve_default_na_tokens_and_literal_headers(tmp_path):
    source = tmp_path / "markers.csv"
    source.write_text("MISSING,value\n1,1\n2,MISSING\n3,-999\n4,NA\n5,\n6,6\n")
    actual = read_csv(source, missing_values=["MISSING", "-999"])
    assert actual.columns.tolist() == ["MISSING", "value"]
    assert actual["value"].isna().tolist() == [False, True, True, True, True, False]
    assert actual["MISSING"].tolist() == [1, 2, 3, 4, 5, 6]


def test_numeric_sentinel_is_observed_unless_explicitly_configured(tmp_path):
    source = tmp_path / "numeric.csv"
    source.write_text("value\n1\n2\n-999\n4\n5\n")
    assert read_csv(source)["value"].tolist() == [1, 2, -999, 4, 5]
    assert read_csv(source, missing_values=["-999"])["value"].isna().sum() == 1


@pytest.mark.parametrize("observed,status", [(4, 2), (5, 0)])
def test_custom_markers_feed_observation_counts_and_insufficient_gate(tmp_path, observed, status):
    source, output = tmp_path / "source.csv", tmp_path / "report.json"
    pd.DataFrame({"value": [1] * observed + [-999] * (10 - observed)}).to_csv(source, index=False)
    assert (
        main(
            [
                "compare",
                str(source),
                str(source),
                "--missing-value=-999",
                "--fail-on-insufficient-data",
                "--output",
                str(output),
            ]
        )
        == status
    )
    feature = json.loads(output.read_text())["scenarios"][0]["drift"]["features"][0]
    assert feature["reference_observed"] == feature["current_observed"] == observed
    assert feature["reference_missing"] == (10 - observed) / 10
    assert feature["insufficient_data"] is (observed < 5)


def test_markers_combine_with_delimiters_selection_and_quality_alerts(tmp_path, capsys):
    reference, current = tmp_path / "reference.csv", tmp_path / "current.csv"
    pd.DataFrame({"id": ["ref"] * 10, "value": range(10)}).to_csv(reference, sep=";", index=False)
    pd.DataFrame({"id": ["cur"] * 10, "value": ["MISSING", -999] + list(range(2, 10))}).to_csv(
        current, sep=";", index=False
    )
    assert (
        main(
            [
                "compare",
                str(reference),
                str(current),
                "--delimiter",
                ";",
                "--columns",
                "value",
                "--missing-value",
                "MISSING",
                "--missing-value=-999",
                "--fail-on-alert",
                "--output",
                "-",
            ]
        )
        == 2
    )
    feature = json.loads(capsys.readouterr().out)["scenarios"][0]["drift"]["features"][0]
    assert feature["quality_alert"]
    assert feature["reference_observed"] == 10 and feature["current_observed"] == 8
    assert feature["current_missing"] == 0.2
