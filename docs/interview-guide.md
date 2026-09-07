# Explain the project in an interview

## A concise description

“ShiftWatch is a Python ML evaluation and data-drift workbench. I compare several classifiers with training-only cross-validation, evaluate an independent holdout, and inspect how synthetic data changes affect the selected model. A React dashboard visualizes exported statistics, and the same Python drift engine compares arbitrary numerical CSV datasets.”

Before using this description, run the project yourself, inspect the code, and be ready to explain and modify it. Describe your own contribution accurately, including any development assistance where relevant.

## Suggested resume entry

**ShiftWatch — ML Evaluation & Data Drift Monitoring**

Python, scikit-learn, SciPy, pandas, React, TypeScript, GitHub Actions

- Developed a reproducible classification and monitoring pipeline with five-fold cross-validation, held-out evaluation, PSI/KS drift tests, multiple-testing adjustment, and missingness checks.
- Built an interactive report dashboard and CSV comparison CLI, with automated tests covering statistical edge cases, report validation, reproducibility, and preprocessing leakage.
- Evaluated four controlled scenarios on UCI Wine; detected four shifted features while model accuracy decreased from 98.1% to 53.7% under a documented synthetic stress test.

Use the third bullet only with the dataset and synthetic-test qualification. Do not turn it into a business-impact claim or a production performance number.

## Questions to prepare for

1. **Why fit scaling inside CV?** Fitting it before CV reveals information about validation data and biases estimates. The test suite spies on every imputer fit to confirm held-out indices never appear.
2. **Why compare to a dummy model?** It provides a transparent baseline and checks whether complex models improve over a trivial decision rule.
3. **Why macro F1?** It gives each class equal weight; accuracy alone can hide weak performance on smaller classes.
4. **Why combine PSI and KS?** PSI is a binned effect-size heuristic; KS supplies distributional evidence. Neither alone is a complete monitoring policy.
5. **Why adjust p-values?** Testing many features increases opportunities for chance findings. BH adjusts within a single report, under assumptions that are documented.
6. **Does a drift alert require retraining?** No. Check data integrity, feature changes, label availability, and actual performance first. The missingness scenario illustrates the distinction.
7. **What can these tests miss?** Changes in joint distributions, interactions, and the relationship between features and labels may be invisible to univariate checks.
8. **Why use JSON between Python and React?** It separates numerical analysis from presentation, makes reports auditable, and permits a static demo without pretending Python runs in the browser.
9. **What would you change for production?** Start with temporal data and stable-window calibration, then add ingestion, authenticated storage, scheduled jobs, observability, and an alert budget.
10. **What is the biggest limitation?** The demo dataset is small and easy, and perturbations are synthetic. The reusable statistical workflow is the main contribution, not the classification score.

## A useful first extension to own

Add a categorical-feature drift test with missing-value handling and a documented multiple-testing policy. Include independent unit tests, expose it through the same report format, and update the dashboard. This turns the initial project into a contribution you can explain in depth.
