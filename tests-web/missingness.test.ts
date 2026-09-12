import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  isAlert,
  parseReport,
  sortFeatures,
  type Feature,
  type Report,
} from '../lib/report.ts';

type Case = {
  name: string;
  reference_rows: number;
  reference_missing: number;
  current_rows: number;
  current_missing: number;
  threshold: number;
  alert: boolean;
};
const cases: Case[] = JSON.parse(
  readFileSync(
    new URL('../tests/fixtures/missingness-thresholds.json', import.meta.url),
    'utf8',
  ),
);

for (const c of cases) {
  void test(`missingness: ${c.name}`, () => {
    const reference = c.reference_missing / c.reference_rows;
    const current = c.current_missing / c.current_rows;
    const feature: Feature = {
      name: 'signal',
      psi: 0,
      ks: 0,
      p_value: 1,
      q_value: 1,
      wasserstein: 0,
      normalized_wasserstein: null,
      reference_mean: 1,
      current_mean: 1,
      reference_missing: reference,
      current_missing: current,
      missing_delta: current - reference,
      reference_observed: c.reference_rows - c.reference_missing,
      current_observed: c.current_rows - c.current_missing,
      quality_alert: c.alert,
      distribution_alert: false,
      alert: c.alert,
      insufficient_data: false,
      histogram: [{ low: 0.5, high: 1.5, reference: 1, current: 1 }],
    };
    assert.equal(isAlert(feature, 0.2, 0.05, c.threshold), c.alert);
    assert.equal(
      sortFeatures([feature], '', true, 0.2, 0.05, c.threshold).length,
      Number(c.alert),
    );
    const report: Report = {
      schema_version: 'shiftwatch/v1',
      kind: 'comparison',
      seed: null,
      dataset: {
        name: c.name,
        rows: c.current_rows,
        features: 1,
        classes: null,
      },
      selected_model: null,
      models: [],
      scenarios: [
        {
          id: 'custom',
          name: c.name,
          description: 'Constant data with controlled missing values',
          synthetic: true,
          metrics: null,
          drift: {
            reference_rows: c.reference_rows,
            current_rows: c.current_rows,
            feature_count: 1,
            alert_count: Number(c.alert),
            config: {
              alpha: 0.05,
              psi_threshold: 0.2,
              missing_threshold: c.threshold,
              bins: 10,
            },
            features: [feature],
          },
        },
      ],
    };
    assert.equal(
      parseReport(report).scenarios[0].drift.alert_count,
      Number(c.alert),
    );
    feature.quality_alert = feature.alert = !c.alert;
    report.scenarios[0].drift.alert_count = Number(!c.alert);
    assert.throws(() => parseReport(report), /Invalid ShiftWatch/);
  });
}
