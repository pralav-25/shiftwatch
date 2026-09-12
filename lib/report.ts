export type HistogramBin = {
  low: number;
  high: number;
  reference: number;
  current: number;
};
export type Feature = {
  name: string;
  psi: number | null;
  ks: number | null;
  p_value: number | null;
  q_value: number | null;
  wasserstein: number | null;
  normalized_wasserstein: number | null;
  reference_mean: number | null;
  current_mean: number | null;
  reference_missing: number;
  current_missing: number;
  missing_delta: number;
  reference_observed: number;
  current_observed: number;
  quality_alert: boolean;
  insufficient_data: boolean;
  distribution_alert: boolean;
  alert: boolean;
  histogram: HistogramBin[];
};
export type Metrics = {
  accuracy: number;
  macro_f1: number;
  log_loss: number;
  accuracy_ci: number[];
  confusion_matrix: number[][];
  class_labels: string[];
  rows: number;
};
export type Scenario = {
  id: string;
  name: string;
  description: string;
  synthetic: boolean;
  metrics: Metrics | null;
  drift: {
    reference_rows: number;
    current_rows: number;
    feature_count: number;
    alert_count: number;
    config: {
      alpha: number;
      psi_threshold: number;
      missing_threshold: number;
      bins: number;
    };
    features: Feature[];
  };
};
export type Report = {
  schema_version: string;
  kind: 'experiment' | 'comparison';
  seed: number | null;
  dataset: {
    name: string;
    rows: number;
    features: number;
    classes: number | null;
  };
  selected_model: string | null;
  models: {
    name: string;
    cv_mean: number;
    cv_std: number;
    cv_folds: number[];
  }[];
  scenarios: Scenario[];
};
function missingnessAlert(delta: number, threshold: number): boolean {
  // Match drift.py's relative-only isclose tolerance at inclusive boundaries.
  // No absolute tolerance: unchanged data must not alert at tiny thresholds.
  const magnitude = Math.abs(delta);
  return magnitude >= threshold ||
    Math.abs(magnitude - threshold) <= 1e-12 * Math.max(magnitude, threshold);
}
export function isAlert(
  f: Feature,
  threshold: number,
  alpha: number,
  missingThreshold: number,
): boolean {
  return (
    (f.psi !== null &&
      f.q_value !== null &&
      f.psi >= threshold &&
      f.q_value <= alpha) ||
    missingnessAlert(f.missing_delta, missingThreshold)
  );
}
export function sortFeatures(
  features: Feature[],
  query: string,
  onlyAlerts: boolean,
  threshold: number,
  alpha: number,
  missing: number,
): Feature[] {
  return features
    .filter(
      (f) =>
        f.name.toLowerCase().includes(query.toLowerCase()) &&
        (!onlyAlerts || isAlert(f, threshold, alpha, missing)),
    )
    .sort(
      (a, b) =>
        Number(isAlert(b, threshold, alpha, missing)) -
          Number(isAlert(a, threshold, alpha, missing)) ||
        (b.psi ?? -1) - (a.psi ?? -1),
    );
}

// Report files are untrusted input. Validate the complete render contract before updating state.
export function parseReport(input: unknown): Report {
  function fail(): never {
    throw new Error(
      'Invalid ShiftWatch report. Export a fresh JSON report with the Python CLI.',
    );
  }
  function obj(x: unknown): Record<string, unknown> {
    if (!x || typeof x !== 'object' || Array.isArray(x)) fail();
    return x as Record<string, unknown>;
  }
  function text(x: unknown): asserts x is string {
    if (typeof x !== 'string' || !x.length || x.length > 2000) fail();
  }
  function number(
    x: unknown,
    lo = -Infinity,
    hi = Infinity,
  ): asserts x is number {
    if (typeof x !== 'number' || !Number.isFinite(x) || x < lo || x > hi)
      fail();
  }
  function count(x: unknown): asserts x is number {
    number(x, 0, 1e9);
    if (!Number.isInteger(x)) fail();
  }
  function boolean(x: unknown) {
    if (typeof x !== 'boolean') fail();
  }
  function nullable(x: unknown, lo = -Infinity, hi = Infinity) {
    if (x !== null) number(x, lo, hi);
  }
  function array(x: unknown, min = 0, max = 200): unknown[] {
    if (!Array.isArray(x) || x.length < min || x.length > max) fail();
    return x;
  }
  const r = obj(input);
  if (
    r.schema_version !== 'shiftwatch/v1' ||
    !['experiment', 'comparison'].includes(String(r.kind))
  )
    fail();
  nullable(r.seed);
  if (r.selected_model !== null) text(r.selected_model);
  const dataset = obj(r.dataset);
  text(dataset.name);
  count(dataset.rows);
  count(dataset.features);
  nullable(dataset.classes, 1, 20);
  const models = array(r.models, 0, 20);
  for (const item of models) {
    const m = obj(item);
    text(m.name);
    number(m.cv_mean, 0, 1);
    number(m.cv_std, 0, 1);
    array(m.cv_folds, 2, 20).forEach((v) => number(v, 0, 1));
  }
  const scenarios = array(r.scenarios, 1, 20),
    ids = new Set();
  for (const item of scenarios) {
    const s = obj(item);
    text(s.id);
    if (ids.has(s.id)) fail();
    ids.add(s.id);
    text(s.name);
    text(s.description);
    boolean(s.synthetic);
    const d = obj(s.drift);
    count(d.reference_rows);
    count(d.current_rows);
    count(d.feature_count);
    count(d.alert_count);
    const c = obj(d.config);
    number(c.alpha, Number.EPSILON, 1 - Number.EPSILON);
    number(c.psi_threshold, Number.EPSILON);
    number(c.missing_threshold, Number.EPSILON, 1);
    number(c.bins, 2, 50);
    count(c.bins);
    const fs = array(d.features, 1, 200),
      names = new Set();
    if (fs.length !== d.feature_count || fs.length !== dataset.features) fail();
    for (const item of fs) {
      const f = obj(item);
      text(f.name);
      if (names.has(f.name)) fail();
      names.add(f.name);
      for (const k of ['psi', 'wasserstein', 'normalized_wasserstein'])
        nullable(f[k], 0);
      for (const k of ['ks', 'p_value', 'q_value']) nullable(f[k], 0, 1);
      nullable(f.reference_mean);
      nullable(f.current_mean);
      number(f.reference_missing, 0, 1);
      number(f.current_missing, 0, 1);
      number(f.missing_delta, -1, 1);
      if (
        Math.abs(
          (f.current_missing as number) -
            (f.reference_missing as number) -
            (f.missing_delta as number),
        ) > 1e-8
      )
        fail();
      count(f.reference_observed);
      count(f.current_observed);
      if (
        (f.reference_observed as number) > (d.reference_rows as number) ||
        (f.current_observed as number) > (d.current_rows as number)
      )
        fail();
      for (const k of [
        'quality_alert',
        'insufficient_data',
        'distribution_alert',
        'alert',
      ])
        boolean(f[k]);
      const quality = missingnessAlert(f.missing_delta as number, c.missing_threshold as number);
      const distribution = f.psi !== null && f.q_value !== null &&
        (f.psi as number) >= (c.psi_threshold as number) &&
        (f.q_value as number) <= (c.alpha as number);
      if (f.quality_alert !== quality || f.distribution_alert !== distribution ||
          f.alert !== (quality || distribution)) fail();
      if (f.insufficient_data !== (Math.min(f.reference_observed as number, f.current_observed as number) < 5)) fail();
      const histogram = array(f.histogram, 0, 100);
      let previousHigh: number | undefined;
      for (const item of histogram) {
        const b = obj(item);
        number(b.low);
        number(b.high);
        if ((b.high as number) <= (b.low as number)) fail();
        if (previousHigh !== undefined && previousHigh !== b.low) fail();
        previousHigh = b.high as number;
        number(b.reference, 0, 1);
        number(b.current, 0, 1);
      }
      if (histogram.length) {
        for (const key of ['reference', 'current']) {
          const total = histogram.reduce<number>(
            (sum, b) => sum + (obj(b)[key] as number),
            0,
          );
          if (Math.abs(total - 1) > 1e-6) fail();
        }
      }
    }
    if (d.alert_count !== fs.filter((f) => obj(f).alert).length) fail();
    if (s.metrics !== null) {
      const m = obj(s.metrics);
      number(m.accuracy, 0, 1);
      number(m.macro_f1, 0, 1);
      number(m.log_loss, 0);
      count(m.rows);
      if (m.rows !== d.current_rows) fail();
      const ci = array(m.accuracy_ci, 2, 2);
      ci.forEach((v) => number(v, 0, 1));
      if ((ci[0] as number) > (ci[1] as number)) fail();
      const labels = array(m.class_labels, 2, 20);
      labels.forEach(text);
      const rows = array(m.confusion_matrix, labels.length, labels.length);
      let total = 0;
      rows.forEach((row) =>
        array(row, labels.length, labels.length).forEach((n) => {
          count(n);
          total += n;
        }),
      );
      if (total !== m.rows) fail();
    }
  }
  return input as Report;
}
