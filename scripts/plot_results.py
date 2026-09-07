"""Render real experiment results for the README. Run from the repository root."""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

report = json.loads(Path("public/reports/demo.json").read_text())
scenarios = report["scenarios"]
plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": "#091717",
                     "axes.labelcolor": "#626c67", "xtick.color": "#626c67",
                     "ytick.color": "#626c67", "font.size": 11})
fig, axes = plt.subplots(1, 2, figsize=(13, 4.7), facecolor="#fbfaf4")
fig.suptitle("ShiftWatch / Detect the shift. Measure the impact.", fontsize=17, x=.06, ha="left", y=.99)
labels = ["Untouched", "Moderate shift", "Severe shift", "Missing data"]
colors = ["#21808d", "#b79062", "#965b40", "#86a58e"]
for ax in axes:
    ax.set_facecolor("#fbfaf4")
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.grid(axis="y", color="#dfe3d8", alpha=.7)
    ax.set_axisbelow(True)
    ax.tick_params(length=0, pad=10)
values = [s["metrics"]["accuracy"] * 100 for s in scenarios]
axes[0].bar(labels, values, color=colors, width=.6)
axes[0].set_ylim(0, 113)
axes[0].set_ylabel("Accuracy (%)")
axes[0].set_title("Model performance on 54 test rows", color="#091717", loc="left", pad=20)
for i, v in enumerate(values):
    axes[0].text(i, v+3, f"{v:.1f}%", ha="center", color="#091717", fontsize=12)
counts = [s["drift"]["alert_count"] for s in scenarios]
axes[1].bar(labels, counts, color=colors, width=.6)
axes[1].set_ylim(0, 5.2)
axes[1].set_yticks(np.arange(0, 6))
axes[1].set_ylabel("Features flagged (of 13)")
axes[1].set_title("Distribution + missingness signals", color="#091717", loc="left", pad=20)
for i, v in enumerate(counts):
    axes[1].text(i, v+.12, str(v), ha="center", color="#091717", fontsize=12)
fig.text(.06, .035, "UCI Wine · seed 42 · logistic regression · PSI ≥ 0.20 & BH q ≤ 0.05, or missingness change ≥ 5 pp\nShifted and missing-data scenarios are synthetic stress tests; original test labels are retained.", color="#626c67", fontsize=10, linespacing=1.8)
fig.subplots_adjust(left=.065, right=.98, top=.78, bottom=.25, wspace=.28)
fig.savefig("docs/experiment-results.png", dpi=160, facecolor=fig.get_facecolor())
