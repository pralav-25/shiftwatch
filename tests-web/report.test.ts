import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  parseReport,
  isAlert,
  sortFeatures,
  type Report,
} from '../lib/report.ts';
const raw = (): Report =>
  JSON.parse(
    readFileSync(
      new URL('../public/reports/demo.json', import.meta.url),
      'utf8',
    ),
  );
void test('accepts the report produced by the real Python pipeline', () => {
  assert.equal(parseReport(raw()).scenarios.length, 4);
});
void test('rejects malformed nested report data before rendering', () => {
  for (const change of [
    (r: Report) => {
      Reflect.set(r.scenarios[0].drift.features[0], 'histogram', null);
    },
    (r: Report) => {
      r.scenarios[0].metrics!.accuracy = Infinity;
    },
    (r: Report) => {
      r.scenarios[0].metrics!.confusion_matrix[0][0] = -1;
    },
    (r: Report) => {
      r.scenarios[0].drift.features[0].q_value = -0.1;
    },
    (r: Report) => {
      r.scenarios[0].drift.features.push(r.scenarios[0].drift.features[0]);
    },
    (r: Report) => {
      r.scenarios[0].drift.features[0].histogram[0].reference = 0.99;
    },
    (r: Report) => {
      r.scenarios = [];
    },
  ]) {
    const r = raw();
    change(r);
    assert.throws(() => parseReport(r), /Invalid ShiftWatch/);
  }
});
void test('requires both effect size and adjusted statistical evidence', () => {
  const f = parseReport(raw()).scenarios[0].drift.features[0];
  assert.equal(
    isAlert({ ...f, psi: 1, q_value: 0.8, missing_delta: 0 }, 0.2, 0.05, 0.05),
    false,
  );
  assert.equal(
    isAlert(
      { ...f, psi: 0.3, q_value: 0.01, missing_delta: 0 },
      0.2,
      0.05,
      0.05,
    ),
    true,
  );
  assert.equal(
    isAlert(
      { ...f, psi: null, q_value: null, missing_delta: 0.3 },
      0.2,
      0.05,
      0.05,
    ),
    true,
  );
});
void test('filters without mutating original feature order', () => {
  const fs = parseReport(raw()).scenarios[2].drift.features;
  const before = fs.map((f) => f.name);
  assert.equal(
    sortFeatures(fs, 'FLAV', false, 0.2, 0.05, 0.05)[0].name,
    'flavanoids',
  );
  assert.equal(sortFeatures(fs, '', true, 0.2, 0.05, 0.05).length, 4);
  assert.deepEqual(
    fs.map((f) => f.name),
    before,
  );
});
