"""Train on UCI Wine; evaluate untouched and synthetically perturbed holdouts."""

from __future__ import annotations

import hashlib
import platform

import numpy as np
import scipy
import sklearn
from sklearn.datasets import load_wine
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, log_loss
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .drift import compare_frames


def _evaluate(model, x, y, seed: int) -> dict:
    prediction = model.predict(x)
    correct = (prediction == y).astype(float)
    rng = np.random.default_rng(seed)
    bootstrap = rng.choice(correct, size=(2000, len(correct)), replace=True).mean(axis=1)
    return {
        "accuracy": float(accuracy_score(y, prediction)),
        "macro_f1": float(f1_score(y, prediction, average="macro", zero_division=0)),
        "log_loss": float(log_loss(y, model.predict_proba(x), labels=model.classes_)),
        "accuracy_ci": np.quantile(bootstrap, [0.025, 0.975]).tolist(),
        "confusion_matrix": confusion_matrix(y, prediction, labels=model.classes_).tolist(),
        "class_labels": [f"Cultivar {i + 1}" for i in model.classes_],
        "rows": len(x),
    }


def run_experiment(seed: int = 42) -> dict:
    dataset = load_wine(as_frame=True)
    x_train, x_test, y_train, y_test = train_test_split(
        dataset.data, dataset.target, test_size=0.3, stratify=dataset.target, random_state=seed
    )
    candidates = {
        "Dummy baseline": DummyClassifier(strategy="most_frequent"),
        "Logistic regression": LogisticRegression(max_iter=2000, C=1.0, random_state=seed),
        "Random forest": RandomForestClassifier(
            n_estimators=200, max_depth=5, min_samples_leaf=2, random_state=seed, n_jobs=1
        ),
    }
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    fitted, results = {}, []
    for name, estimator in candidates.items():
        pipeline = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), estimator)
        scores = cross_val_score(pipeline, x_train, y_train, cv=cv, scoring="f1_macro", n_jobs=1)
        pipeline.fit(x_train, y_train)
        fitted[name] = pipeline
        results.append(
            {
                "name": name,
                "cv_mean": float(scores.mean()),
                "cv_std": float(scores.std()),
                "cv_folds": scores.tolist(),
            }
        )
    selected = max(results, key=lambda row: row["cv_mean"])["name"]
    model = fitted[selected]
    standard_deviation = x_train.std(ddof=0)
    shifted_features = ["alcohol", "flavanoids", "color_intensity", "proline"]
    scenarios = []
    definitions = [
        (
            "reference",
            "Untouched holdout",
            "Independent, stratified test split. No changes applied.",
        ),
        (
            "moderate",
            "Moderate shift",
            "Four features shifted by 0.75 training standard deviations.",
        ),
        ("severe", "Severe shift", "Four features shifted by 2 training standard deviations."),
        (
            "missing",
            "Missing data",
            "30% of values removed from three features with a fixed random seed.",
        ),
    ]
    for scenario_id, name, description in definitions:
        current = x_test.copy()
        if scenario_id in {"moderate", "severe"}:
            magnitude = 0.75 if scenario_id == "moderate" else 2.0
            for feature in shifted_features:
                current[feature] += magnitude * standard_deviation[feature]
        if scenario_id == "missing":
            rng = np.random.default_rng(seed)
            for feature in ["alcohol", "flavanoids", "proline"]:
                rows = rng.choice(len(current), size=round(0.3 * len(current)), replace=False)
                current.iloc[rows, current.columns.get_loc(feature)] = np.nan
        scenarios.append(
            {
                "id": scenario_id,
                "name": name,
                "description": description,
                "synthetic": scenario_id != "reference",
                "drift": compare_frames(x_train, current),
                "metrics": _evaluate(model, current, y_test.to_numpy(), seed),
            }
        )
    fingerprint = hashlib.sha256(dataset.data.to_csv(index=False).encode()).hexdigest()
    return {
        "schema_version": "shiftwatch/v1",
        "kind": "experiment",
        "seed": seed,
        "dataset": {
            "name": "UCI Wine",
            "rows": len(dataset.data),
            "features": len(dataset.data.columns),
            "classes": 3,
            "source": "https://archive.ics.uci.edu/dataset/109/wine",
            "sha256": fingerprint,
        },
        "split": {
            "train_rows": len(x_train),
            "test_rows": len(x_test),
            "train_indices": x_train.index.tolist(),
            "test_indices": x_test.index.tolist(),
        },
        "selected_model": selected,
        "models": results,
        "scenarios": scenarios,
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "sklearn": sklearn.__version__,
        },
    }
