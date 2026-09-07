# Model card: Wine cultivar classifier

| Field | Value |
|---|---|
| Intended use | Educational classification and monitoring experiments |
| Out-of-scope use | Production quality control, safety decisions, or general-purpose classification |
| Training data | 124 rows from scikit-learn's UCI Wine copy |
| Evaluation data | 54 stratified held-out rows; fixed seed 42 |
| Inputs | 13 numerical chemical measurements |
| Output | One of three cultivar classes |
| Selection | Maximum mean macro F1 in five-fold training-only CV |
| Selected estimator | Logistic regression, C=1, max_iter=2,000 |
| Preprocessing | Training-fitted median imputation and standard scaling |
| Baseline accuracy | 53 / 54 = 98.15% on the untouched holdout |
| Stress accuracy | 45 / 54 moderate shift; 29 / 54 severe shift |
| Training environment | Exact versions in `requirements.lock`; run metadata in report |

This is a small, relatively separable dataset. The high score should not be extrapolated to other datasets. The model has not been evaluated for real deployment, temporal robustness, subgroup performance, or adversarial manipulation. Its probabilities are not separately calibrated.

Missing-value imputation is fitted on clean training data. The missingness stress test has the same accuracy as the untouched holdout for this seed, but this does not establish general robustness to missing inputs.

The experiment returns fitted-model evaluations, not a distributed prediction service or persisted model artifact. Re-running the CLI retrains the models. The static dashboard shows actual exported results and cannot serve live predictions.

Dataset credit: Stefan Aeberhard and M. Forina, Wine, UCI Machine Learning Repository, [10.24432/C5PC7J](https://doi.org/10.24432/C5PC7J), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Data modifications include split selection, zero-based label encoding inherited from scikit-learn, and synthetic shift/missingness scenarios.
