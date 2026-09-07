# Methodology

## Experiment design

`load_wine(as_frame=True)` supplies 178 observations with 13 chemical measurements and three cultivar labels. A stratified 70/30 split with seed 42 assigns 124 rows to training and 54 to testing. Exact row indices and the SHA-256 fingerprint of the serialized feature table are saved in the report.

Each candidate is a scikit-learn pipeline: median imputation → standard scaling → estimator. Imputation and scaling fit only the training portion of each cross-validation fold. Five-fold stratified CV uses macro F1. The highest mean score selects the model, then its pipeline fits the full training split once. Holdout results do not influence selection. No hyperparameter search is performed; model settings are explicit in `experiment.py`.

The dummy classifier predicts the training majority class. Logistic regression uses C=1 and at most 2,000 iterations. Random forest uses 200 trees, maximum depth 5, and a minimum of two samples per leaf. Scaling is unnecessary for the forest but keeps the preprocessing structure consistent.

## Stress scenarios

The original holdout is evaluated without changes. Moderate and severe scenarios add respectively 0.75 and 2 times the **training** standard deviation to alcohol, flavanoids, color intensity, and proline. The missingness scenario removes `round(0.30 × 54) = 16` entries from each of alcohol, flavanoids, and proline, using a seeded generator.

All scenarios preserve original labels. They probe a fitted model's behavior under controlled corruption. They do not demonstrate what labels would be under a real changed data-generating process and should not be described as production concept drift.

## Numerical drift

The reference table defines the expected distribution. Comparison tables must have the same named numerical columns; ordering does not matter. Null values are tracked separately. Infinity is rejected. Fewer than five finite observations in either side results in an explicit `insufficient_data` flag and null distribution statistics.

### Population Stability Index

Reference decile boundaries define histogram bins. Duplicate boundaries are removed. The first and last bins extend to negative and positive infinity so values beyond the original range are counted. Constant reference data uses a narrow central bin with overflow bins on each side.

Each bin receives 0.5 pseudo-counts before normalization (Jeffreys-style smoothing):

`p_i = (reference_count_i + 0.5) / (reference_n + 0.5 × bins)`

`q_i = (current_count_i + 0.5) / (current_n + 0.5 × bins)`

`PSI = Σ (q_i − p_i) × log(q_i / p_i)`

The result depends on binning and smoothing, especially with small samples. The default 0.20 threshold is a configurable effect-size heuristic. It is not a p-value. Charts deliberately use shared equal-width bins for readability; they are not the bins used to compute PSI.

### KS and multiple comparisons

SciPy's two-sided `ks_2samp` compares the empirical cumulative distributions of nonmissing values. Valid feature tests are adjusted together with the Benjamini–Hochberg procedure. Sorted p-values are multiplied by `number_of_tests / rank`, followed by a reverse cumulative minimum and clipping at one.

A distribution alert requires both PSI ≥ threshold and adjusted p ≤ alpha. BH's usual false-discovery guarantees require independence or suitable positive dependence. Correlated real-world features may violate those assumptions. KS assumes independent continuous observations; rounded values and ties affect p-value calibration. The code uses SciPy's automatic method and does not claim exact calibration for Wine's rounded measurements.

The report also includes Wasserstein distance in original feature units and normalized by the reference population standard deviation. Normalized distance is null when the reference standard deviation is zero.

### Missingness

Missing-rate changes are measured in absolute percentage points. A change of at least 0.05 triggers a separate quality alert, even if too few observations remain for distribution testing. Both increased and decreased missingness count because either can indicate a pipeline change.

## Model evaluation

Accuracy, macro F1, multiclass log loss, and the confusion matrix describe each test scenario. Accuracy intervals are 2.5th/97.5th percentile intervals from 2,000 seeded bootstrap resamples of the correctness vector. They capture test-sample variation conditional on this fitted model. They exclude variation from retraining, model selection, and dataset sampling before the train/test split. Percentile intervals may be overly optimistic near perfect accuracy or on very small samples.

## Report and dashboard contract

`shiftwatch/v1` stores scenarios, drift configuration, per-feature statistics and histograms, and optional model evaluation. CSV-only reports intentionally set model metrics to null. The dashboard rejects malformed nested data, nonfinite values, inconsistent matrix sizes, and invalid histogram proportions before updating state. It loads up to 5 MB, 20 scenarios, and 200 features. Python reports with more features still work through the CLI/library.

The browser changes exploratory PSI thresholds and recomputes flags using existing statistics. It never recomputes KS tests or trains a model. Export records the selected PSI threshold and recomputed flags across all scenarios. Report imports remain in memory until reload; there is no backend upload or storage.

Optional, feature-detected WebMCP tools expose the selected drift summary and scenario selection. Runtime validation requires a browser supporting the proposed API. Standard buttons and controls remain the primary interface.

## Extension path

Useful next steps are categorical drift, multivariate tests, calibration on stable historical windows, time-aware evaluation, and labeled concept-drift checks. A real deployment also needs ingestion, authentication, retention controls, scheduled runs, and an alert budget. None is implied by this demonstration.

## Primary references

- [Wine dataset and attribution](https://archive.ics.uci.edu/dataset/109/wine)
- [scikit-learn: preventing data leakage](https://scikit-learn.org/stable/common_pitfalls.html)
- [SciPy: two-sample KS test](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.ks_2samp.html)
- [Benjamini and Hochberg (1995), original paper](https://doi.org/10.1111/j.2517-6161.1995.tb02031.x)
