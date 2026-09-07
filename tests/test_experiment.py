import json

import pytest
from sklearn.impute import SimpleImputer

from shiftwatch.experiment import run_experiment


@pytest.fixture(scope="module")
def report():
    return run_experiment()


def test_split_disjoint_and_covers_dataset(report):
    train, test = set(report["split"]["train_indices"]), set(report["split"]["test_indices"])
    assert not train & test
    assert len(train) == 124 and len(test) == 54
    assert train | test == set(range(178))


def test_selection_uses_only_cross_validation(report):
    assert report["selected_model"] == max(report["models"], key=lambda m: m["cv_mean"])["name"]
    assert all(len(m["cv_folds"]) == 5 for m in report["models"])


def test_preprocessors_never_fit_on_test_rows(monkeypatch, report):
    original_fit, fits = SimpleImputer.fit, []

    def spy(self, x, y=None):
        fits.append(set(x.index))
        return original_fit(self, x, y)

    monkeypatch.setattr(SimpleImputer, "fit", spy)
    rerun = run_experiment()
    training = set(report["split"]["train_indices"])
    assert len(fits) == 18  # 3 candidates × (5 folds + one final fit)
    assert all(rows <= training for rows in fits)
    assert sum(rows == training for rows in fits) == 3
    assert rerun == report


def test_stress_scenarios_are_labeled_and_metrics_consistent(report):
    assert [s["synthetic"] for s in report["scenarios"]] == [False, True, True, True]
    baseline, _, severe, missing = report["scenarios"]
    assert severe["metrics"]["accuracy"] < baseline["metrics"]["accuracy"]
    assert severe["drift"]["alert_count"] >= 4
    assert missing["drift"]["alert_count"] >= 3
    for s in report["scenarios"]:
        m = s["metrics"]
        assert sum(map(sum, m["confusion_matrix"])) == 54
        assert 0 <= m["accuracy_ci"][0] <= m["accuracy_ci"][1] <= 1
    json.dumps(report, allow_nan=False)
