import { isAlert, type Feature, type Scenario } from './report.ts';

export type AlertChange =
  | 'new'
  | 'cleared'
  | 'persistent'
  | 'none'
  | 'unavailable';
export type FeatureComparison = {
  name: string;
  baseline: Feature | null;
  current: Feature | null;
  psiDelta: number | null;
  missingDelta: number | null;
  alertChange: AlertChange;
};

export function metricDelta(
  current: number | null,
  baseline: number | null,
): number | null {
  return current === null || baseline === null ? null : current - baseline;
}

/** Match by feature name; never interpret absent measurements as zero. */
export function compareScenarios(
  baseline: Scenario,
  current: Scenario,
  psiThreshold: number,
): FeatureComparison[] {
  const before = new Map(
    baseline.drift.features.map((feature) => [feature.name, feature]),
  );
  const after = new Map(
    current.drift.features.map((feature) => [feature.name, feature]),
  );
  const alerted = (feature: Feature, scenario: Scenario) =>
    isAlert(
      feature,
      psiThreshold,
      scenario.drift.config.alpha,
      scenario.drift.config.missing_threshold,
    );
  const order: Record<AlertChange, number> = {
    new: 0,
    persistent: 1,
    cleared: 2,
    unavailable: 3,
    none: 4,
  };
  return [...new Set([...before.keys(), ...after.keys()])]
    .map((name): FeatureComparison => {
      const a = before.get(name) ?? null;
      const b = after.get(name) ?? null;
      let alertChange: AlertChange = 'unavailable';
      if (a && b) {
        const wasAlert = alerted(a, baseline);
        const nowAlert = alerted(b, current);
        alertChange = nowAlert
          ? wasAlert
            ? 'persistent'
            : 'new'
          : wasAlert
            ? 'cleared'
            : 'none';
      }
      return {
        name,
        baseline: a,
        current: b,
        alertChange,
        psiDelta: metricDelta(b?.psi ?? null, a?.psi ?? null),
        missingDelta: a && b ? b.current_missing - a.current_missing : null,
      };
    })
    .sort(
      (a, b) =>
        order[a.alertChange] - order[b.alertChange] ||
        Math.abs(b.psiDelta ?? 0) - Math.abs(a.psiDelta ?? 0) ||
        a.name.localeCompare(b.name),
    );
}
