import json

import pandas as pd
import pytest

from shiftwatch.cli import main


def test_select_features_excludes_labels_and_preserves_requested_order(tmp_path):
    ref, cur, output = [tmp_path / name for name in ("ref.csv", "cur.csv", "report.json")]
    pd.DataFrame({"id": [f"r{i}" for i in range(10)], "a": range(10), "b": range(10, 20)}).to_csv(
        ref, index=False
    )
    pd.DataFrame({"label": ["pass"] * 10, "b": range(10, 20), "a": range(10)}).to_csv(
        cur, index=False
    )
    before = [path.read_bytes() for path in (ref, cur)]
    assert (
        main(["compare", str(ref), str(cur), "--columns", "b", "a", "--output", str(output)]) == 0
    )
    report = json.loads(output.read_text())
    drift = report["scenarios"][0]["drift"]
    assert report["dataset"]["features"] == 2
    assert [row["name"] for row in drift["features"]] == ["b", "a"]
    assert drift["alert_count"] == 0
    assert [path.read_bytes() for path in (ref, cur)] == before


@pytest.mark.parametrize(
    "columns,message",
    [
        (["a", "a"], "unique"),
        (["missing"], "Reference is missing"),
        (["ref_only"], "Current is missing"),
        (["text"], "real numeric"),
    ],
)
def test_selection_errors_preserve_existing_report(tmp_path, capsys, columns, message):
    ref, cur, output = [tmp_path / name for name in ("ref.csv", "cur.csv", "report.json")]
    pd.DataFrame({"a": range(10), "ref_only": range(10), "text": ["word"] * 10}).to_csv(
        ref, index=False
    )
    pd.DataFrame({"a": range(10), "text": ["word"] * 10}).to_csv(cur, index=False)
    output.write_text("old report")
    with pytest.raises(SystemExit) as exc:
        main(["compare", str(ref), str(cur), "--columns", *columns, "--output", str(output)])
    assert exc.value.code == 2
    assert message in capsys.readouterr().err
    assert output.read_text() == "old report"


def test_without_selection_all_features_are_still_validated(tmp_path):
    path = tmp_path / "mixed.csv"
    pd.DataFrame({"a": range(10), "id": ["record"] * 10}).to_csv(path, index=False)
    with pytest.raises(SystemExit):
        main(["compare", str(path), str(path), "--output", "-"])
