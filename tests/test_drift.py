import numpy as np
import pandas as pd
import pytest

from shiftwatch.drift import bh_adjust, compare_frames, population_stability_index


def frame(values):
    return pd.DataFrame({"signal": values})


def test_identical_data_has_no_drift():
    x = frame(np.arange(100, dtype=float))
    report = compare_frames(x, x)
    feature = report["features"][0]
    assert report["alert_count"] == 0
    assert feature["psi"] == 0
    assert feature["ks"] == 0
    assert feature["q_value"] == 1


def test_detects_large_shift_and_counts_overflow():
    ref = frame(np.arange(100, dtype=float))
    cur = ref + 1000
    feature = compare_frames(ref, cur)["features"][0]
    assert feature["distribution_alert"]
    assert feature["psi"] > 1
    assert feature["wasserstein"] == pytest.approx(1000)
    assert sum(b["current"] for b in feature["histogram"]) == pytest.approx(1)


@pytest.mark.parametrize("direction", [-1, 1])
def test_constant_reference_detects_shift_in_either_direction(direction):
    feature = compare_frames(frame(np.ones(40)), frame(np.ones(40) + direction))["features"][0]
    assert feature["distribution_alert"]
    assert feature["normalized_wasserstein"] is None


def test_bh_correction_known_values_and_order():
    assert bh_adjust([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.04, 0.04])
    assert bh_adjust([]) == []
    assert bh_adjust([0, 1]) == [0, 1]
    with pytest.raises(ValueError):
        bh_adjust([float("nan")])


def test_missingness_not_hidden_by_dropping_nulls():
    ref = frame(np.arange(20, dtype=float))
    cur = ref.copy()
    cur.iloc[:6] = np.nan
    feature = compare_frames(ref, cur)["features"][0]
    assert feature["quality_alert"]
    assert feature["missing_delta"] == 0.3
    assert feature["current_observed"] == 14


def test_all_missing_has_explicit_insufficient_data():
    feature = compare_frames(frame(np.arange(20)), frame([np.nan] * 20))["features"][0]
    assert feature["insufficient_data"]
    assert feature["psi"] is None
    assert feature["q_value"] is None
    assert feature["histogram"] == []
    assert feature["quality_alert"]


def test_all_missing_reference_is_reported():
    feature = compare_frames(frame([np.nan] * 20), frame(np.arange(20)))["features"][0]
    assert feature["insufficient_data"] and feature["quality_alert"]


def test_column_order_is_aligned_by_name():
    ref = pd.DataFrame({"a": range(20), "b": range(100, 120)})
    assert compare_frames(ref, ref[["b", "a"]])["alert_count"] == 0


@pytest.mark.parametrize(
    "current",
    [
        frame([1, 2]),
        frame([1, 2, 3, 4, float("inf")]),
        frame(["a"] * 10),
        pd.DataFrame({"wrong_name": range(20)}),
        pd.DataFrame(np.ones((20, 2)), columns=["signal", "signal"]),
    ],
)
def test_rejects_invalid_inputs(current):
    with pytest.raises(ValueError):
        compare_frames(frame(range(20)), current)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"alpha": 0},
        {"alpha": 1},
        {"psi_threshold": -1},
        {"psi_threshold": float("nan")},
        {"missing_threshold": 0},
        {"bins": 1},
    ],
)
def test_rejects_invalid_configuration(kwargs):
    with pytest.raises(ValueError):
        compare_frames(frame(range(20)), frame(range(20)), **kwargs)


def test_psi_rejects_nonfinite_or_empty_arrays():
    for invalid in [[], [np.nan], [np.inf]]:
        with pytest.raises(ValueError):
            population_stability_index(np.arange(10), np.array(invalid))


@pytest.mark.parametrize("bins", [2.5, True, False, float("nan"), "10"])
def test_bins_must_be_integers(bins):
    with pytest.raises(ValueError):
        compare_frames(frame(range(20)), frame(range(20)), bins=bins)
    with pytest.raises(ValueError):
        population_stability_index(np.arange(20), np.arange(20), bins=bins)


def test_complex_features_are_not_silently_cast_to_real():
    with pytest.raises(ValueError, match="real numeric"):
        compare_frames(frame([1 + 2j] * 20), frame([1 + 3j] * 20))
