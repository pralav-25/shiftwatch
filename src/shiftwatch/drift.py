"""Univariate drift with baseline-only bins and multiple-testing correction.

KS tests assume independent continuous observations; rounded/discrete features and
small samples make p-values approximate. Missingness is monitored separately.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp, wasserstein_distance


def bh_adjust(pvalues: list[float]) -> list[float]:
    """Benjamini-Hochberg adjusted p-values, preserving input order."""
    p = np.asarray(pvalues, dtype=float)
    if p.ndim != 1 or not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError("p-values must be finite and between zero and one")
    if not len(p):
        return []
    order = np.argsort(p, kind="stable")
    adjusted = np.minimum.accumulate((p[order] * len(p) / np.arange(1, len(p) + 1))[::-1])[::-1]
    result = np.empty_like(p)
    result[order] = np.minimum(adjusted, 1.0)
    return result.tolist()


def _edges(reference: np.ndarray, bins: int) -> np.ndarray:
    inner = np.unique(np.quantile(reference, np.linspace(0, 1, bins + 1)[1:-1]))
    if np.ptp(reference) == 0:
        value = float(reference[0])
        delta = max(abs(value) * 1e-6, 1e-6)
        inner = np.array([value - delta, value + delta])
    # Overflow bins ensure current values outside the reference range are counted.
    return np.r_[-np.inf, inner, np.inf]


def population_stability_index(reference: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
    """PSI with reference quantiles and Jeffreys (0.5-count) smoothing."""
    if not 2 <= bins <= 50:
        raise ValueError("bins must be between 2 and 50")
    ref, cur = np.asarray(reference, float), np.asarray(current, float)
    if ref.ndim != 1 or cur.ndim != 1 or not len(ref) or not len(cur):
        raise ValueError("PSI requires two nonempty one-dimensional arrays")
    if not np.isfinite(ref).all() or not np.isfinite(cur).all():
        raise ValueError("PSI inputs must be finite")
    edges = _edges(ref, bins)
    a = np.histogram(ref, edges)[0].astype(float) + 0.5
    b = np.histogram(cur, edges)[0].astype(float) + 0.5
    a, b = a / a.sum(), b / b.sum()
    return float(np.sum((b - a) * np.log(b / a)))


def _histogram(ref: np.ndarray, cur: np.ndarray) -> list[dict]:
    if not len(ref) or not len(cur):
        return []
    # Display-only, equal-width shared bins. These are intentionally distinct from PSI bins.
    low, high = min(ref.min(), cur.min()), max(ref.max(), cur.max())
    if low == high:
        low, high = low - 0.5, high + 0.5
    edges = np.linspace(low, high, 13)
    a, b = np.histogram(ref, edges)[0] / len(ref), np.histogram(cur, edges)[0] / len(cur)
    return [
        {
            "low": float(edges[i]),
            "high": float(edges[i + 1]),
            "reference": float(a[i]),
            "current": float(b[i]),
        }
        for i in range(len(a))
    ]


def _validate(frame: pd.DataFrame, label: str) -> None:
    if len(frame) < 5 or len(frame.columns) == 0:
        raise ValueError(f"{label} needs at least 5 rows and one numeric feature")
    if frame.columns.has_duplicates or not all(isinstance(c, str) for c in frame.columns):
        raise ValueError(f"{label} requires unique string column names")
    if not all(pd.api.types.is_numeric_dtype(t) for t in frame.dtypes):
        raise ValueError(f"{label} must contain only numeric features; remove IDs and labels")
    if np.isinf(frame.to_numpy(dtype=float)).any():
        raise ValueError(f"{label} contains infinity; use missing values or correct the input")


def compare_frames(
    reference: pd.DataFrame,
    current: pd.DataFrame,
    *,
    alpha: float = 0.05,
    psi_threshold: float = 0.2,
    missing_threshold: float = 0.05,
    bins: int = 10,
) -> dict:
    """Compare numeric feature tables; flags need both effect size and evidence.

    Distribution alert = PSI >= threshold AND BH-adjusted KS p <= alpha.
    Quality alert = absolute missing-rate change >= missing_threshold.
    Fewer than five observed values yields an explicit insufficient-data result.
    """
    if not 0 < alpha < 1 or not np.isfinite(psi_threshold) or psi_threshold <= 0:
        raise ValueError("alpha must be in (0, 1) and PSI threshold must be finite and positive")
    if not 0 < missing_threshold <= 1 or not 2 <= bins <= 50:
        raise ValueError("missing threshold must be in (0, 1] and bins must be in [2, 50]")
    _validate(reference, "Reference")
    _validate(current, "Current")
    if set(reference.columns) != set(current.columns):
        raise ValueError("Reference and current must have exactly the same feature columns")
    features = []
    for name in reference.columns:
        ref = reference[name].dropna().to_numpy(dtype=float)
        cur = current[name].dropna().to_numpy(dtype=float)
        enough = min(len(ref), len(cur)) >= 5
        ref_missing = float(reference[name].isna().mean())
        cur_missing = float(current[name].isna().mean())
        ks = ks_2samp(ref, cur) if enough else None
        scale = float(np.std(ref)) if len(ref) else 0.0
        features.append(
            {
                "name": name,
                "psi": population_stability_index(ref, cur, bins) if enough else None,
                "ks": float(ks.statistic) if ks is not None else None,
                "p_value": float(ks.pvalue) if ks is not None else None,
                "q_value": None,
                "wasserstein": float(wasserstein_distance(ref, cur)) if enough else None,
                "normalized_wasserstein": (
                    float(wasserstein_distance(ref, cur) / scale) if enough and scale > 0 else None
                ),
                "reference_mean": float(np.mean(ref)) if len(ref) else None,
                "current_mean": float(np.mean(cur)) if len(cur) else None,
                "reference_missing": ref_missing,
                "current_missing": cur_missing,
                "missing_delta": cur_missing - ref_missing,
                "reference_observed": len(ref),
                "current_observed": len(cur),
                "quality_alert": abs(cur_missing - ref_missing) >= missing_threshold,
                "insufficient_data": not enough,
                "distribution_alert": False,
                "histogram": _histogram(ref, cur),
            }
        )
    valid = [f for f in features if f["p_value"] is not None]
    for feature, qvalue in zip(valid, bh_adjust([f["p_value"] for f in valid]), strict=True):
        feature["q_value"] = qvalue
        feature["distribution_alert"] = qvalue <= alpha and feature["psi"] >= psi_threshold
    for feature in features:
        feature["alert"] = feature["distribution_alert"] or feature["quality_alert"]
    return {
        "reference_rows": len(reference),
        "current_rows": len(current),
        "feature_count": len(features),
        "alert_count": sum(f["alert"] for f in features),
        "config": {
            "alpha": alpha,
            "psi_threshold": psi_threshold,
            "missing_threshold": missing_threshold,
            "bins": bins,
        },
        "features": features,
    }
