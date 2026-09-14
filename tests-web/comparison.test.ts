import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import { compareScenarios, metricDelta } from '../lib/comparison.ts';
import type { Feature, Report, Scenario } from '../lib/report.ts';

const demo = JSON.parse(
  readFileSync(new URL('../public/reports/demo.json', import.meta.url), 'utf8'),
) as Report;
const feature = (name: string, overrides: Partial<Feature> = {}): Feature => ({
  ...structuredClone(demo.scenarios[0].drift.features[0]),
  name,
  psi: 0.1,
  q_value: 0.01,
  current_missing: 0,
  missing_delta: 0,
  ...overrides,
});
const scenario = (
  features: Feature[],
  overrides: Partial<Scenario['drift']['config']> = {},
): Scenario => ({
  ...structuredClone(demo.scenarios[0]),
  drift: {
    ...structuredClone(demo.scenarios[0].drift),
    features,
    feature_count: features.length,
    config: {
      alpha: 0.05,
      psi_threshold: 0.2,
      missing_threshold: 0.05,
      bins: 10,
      ...overrides,
    },
  },
});

void test('matches features by name, classifies new/cleared/persistent alerts, and computes signed changes', () => {
  const before = scenario([
    feature('new'),
    feature('cleared', { psi: 0.4 }),
    feature('persistent', { psi: 0.3 }),
  ]);
  const after = scenario([
    feature('persistent', { psi: 0.6 }),
    feature('cleared'),
    feature('new', { psi: 0.5, current_missing: 0.2, missing_delta: 0.2 }),
  ]);
  const original = structuredClone([before, after]);
  const rows = compareScenarios(before, after, 0.2);
  assert.deepEqual(
    rows.map((row) => [row.name, row.alertChange]),
    [
      ['new', 'new'],
      ['persistent', 'persistent'],
      ['cleared', 'cleared'],
    ],
  );
  assert.ok(Math.abs(rows[0].psiDelta! - 0.4) < 1e-12);
  assert.equal(rows[0].missingDelta, 0.2);
  assert.ok(rows[2].psiDelta! < 0);
  assert.deepEqual([before, after], original);
});

void test('does not invent deltas or cleared alerts for missing features and measurements', () => {
  const rows = compareScenarios(
    scenario([
      feature('before-only', { psi: 0.6 }),
      feature('no-psi', { psi: null }),
    ]),
    scenario([feature('after-only'), feature('no-psi')]),
    0.2,
  );
  assert.equal(
    rows.find((row) => row.name === 'before-only')?.alertChange,
    'unavailable',
  );
  assert.equal(
    rows.find((row) => row.name === 'after-only')?.missingDelta,
    null,
  );
  assert.equal(rows.find((row) => row.name === 'no-psi')?.psiDelta, null);
  assert.equal(metricDelta(null, 0.8), null);
  assert.equal(metricDelta(0.8, null), null);
  assert.equal(metricDelta(0, 0), 0);
});

void test('uses the selected PSI threshold and each scenario’s own significance and missingness rules', () => {
  const before = scenario(
    [
      feature('significance', { psi: 0.3, q_value: 0.03 }),
      feature('missing', { missing_delta: 0.06 }),
    ],
    { alpha: 0.01, missing_threshold: 0.1 },
  );
  const after = scenario([
    feature('significance', { psi: 0.3, q_value: 0.03 }),
    feature('missing', { missing_delta: 0.06 }),
  ]);
  assert.deepEqual(
    compareScenarios(before, after, 0.2).map((row) => row.alertChange),
    ['new', 'new'],
  );
  const raised = compareScenarios(before, after, 0.4);
  assert.equal(
    raised.find((row) => row.name === 'significance')?.alertChange,
    'none',
  );
  assert.equal(
    raised.find((row) => row.name === 'missing')?.alertChange,
    'new',
  );
});

void test('identical scenarios have no new or cleared alerts and zero available deltas', () => {
  const input = demo.scenarios[0];
  for (const row of compareScenarios(input, input, 0.2)) {
    assert.ok(['none', 'persistent'].includes(row.alertChange));
    assert.equal(row.psiDelta, row.current?.psi === null ? null : 0);
    assert.equal(row.missingDelta, 0);
  }
});
