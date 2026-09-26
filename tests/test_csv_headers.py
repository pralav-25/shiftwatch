import pandas as pd
import pytest

from shiftwatch.cli import main, read_csv


@pytest.mark.parametrize(
    "header,rows", [(",value", "1,2\n"), ("value,", "1,2\n"), ('"",value', "1,2\n"), ('""', "1\n")]
)
@pytest.mark.parametrize("prefix", ["", "\ufeff\n"])
def test_empty_headers_are_rejected_before_pandas_invents_names(
    tmp_path, capsys, header, rows, prefix
):
    source, output = tmp_path / "empty-header.csv", tmp_path / "report.json"
    source.write_text(prefix + header + "\n" + rows * 5, encoding="utf-8")
    output.write_text("existing report")
    with pytest.raises(SystemExit) as exc:
        main(["compare", str(source), str(source), "--output", str(output)])
    assert exc.value.code == 2
    assert "CSV headers must not be empty" in capsys.readouterr().err
    assert output.read_text() == "existing report"


def test_literal_unnamed_header_is_not_mistaken_for_missing_header(tmp_path):
    source = tmp_path / "literal.csv"
    expected = pd.DataFrame({"Unnamed: 0": range(5), " ": range(5)})
    expected.to_csv(source, index=False)
    pd.testing.assert_frame_equal(read_csv(source), expected)
