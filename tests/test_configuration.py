import json
from fractions import Fraction

import numpy as np
import pandas as pd
import pytest

from shiftwatch.drift import compare_frames


@pytest.mark.parametrize("name", ["alpha", "psi_threshold", "missing_threshold"])
@pytest.mark.parametrize(
    "value",
    [
        True,
        False,
        np.bool_(True),
        "0.2",
        None,
        [0.2],
        np.array([0.2]),
        complex(0.2, 0),
        float("nan"),
        float("inf"),
        10**1000,
    ],
)
def test_invalid_scalar_settings_raise_value_error(name, value):
    frame = pd.DataFrame({"value": range(10)})
    with pytest.raises(ValueError, match="finite real number"):
        compare_frames(frame, frame, **{name: value})


def test_numpy_and_rational_settings_produce_portable_json():
    frame = pd.DataFrame({"value": range(10)})
    report = compare_frames(
        frame,
        frame,
        alpha=np.float32(0.05),
        psi_threshold=Fraction(1, 5),
        missing_threshold=np.float64(0.1),
        bins=np.int64(5),
    )
    config = json.loads(json.dumps(report, allow_nan=False))["config"]
    assert config == {
        "alpha": pytest.approx(0.05),
        "psi_threshold": 0.2,
        "missing_threshold": 0.1,
        "bins": 5,
    }
    assert type(report["config"]["bins"]) is int


@pytest.mark.parametrize("alpha", [5e-324, 1e-20, 0.05, 0.9999999999999999])
@pytest.mark.parametrize("threshold", [5e-324, 1e-20, 0.2])
def test_finite_threshold_boundaries_match_dashboard_contract(alpha, threshold):
    frame = pd.DataFrame({"value": range(10)})
    report = compare_frames(
        frame, frame, alpha=alpha, psi_threshold=threshold, missing_threshold=threshold
    )
    assert report["alert_count"] == 0
    assert json.loads(json.dumps(report, allow_nan=False))["config"] == {
        "alpha": alpha,
        "psi_threshold": threshold,
        "missing_threshold": threshold,
        "bins": 10,
    }
