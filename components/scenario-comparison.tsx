'use client';
/* oxlint-disable jsx-a11y/no-noninteractive-tabindex -- Labeled overflow regions need keyboard focus so their comparison tables can be scrolled on narrow screens. */

import { useMemo, useState } from 'react';
import {
  compareScenarios,
  metricDelta,
  type AlertChange,
} from '@/lib/comparison';
import { isAlert, type Scenario } from '@/lib/report';

const number = (value: number | null) =>
  value === null ? '—' : value.toFixed(3);
const percent = (value: number | null) =>
  value === null ? '—' : `${(value * 100).toFixed(1)}%`;
const delta = (value: number | null, percentage = false) => {
  if (value === null) return '—';
  const rounded = Number(
    (value * (percentage ? 100 : 1)).toFixed(percentage ? 1 : 3),
  );
  return `${rounded > 0 ? '+' : ''}${rounded.toFixed(percentage ? 1 : 3)}${percentage ? ' pp' : ''}`;
};
const labels: Record<AlertChange, string> = {
  new: 'New alert',
  cleared: 'Cleared alert',
  persistent: 'Alert in both',
  none: 'No alert',
  unavailable: 'Not comparable',
};

export function ScenarioComparison({
  scenarios,
  current,
  threshold,
}: {
  scenarios: Scenario[];
  current: Scenario;
  threshold: number;
}) {
  const [baselineId, setBaselineId] = useState('');
  const [query, setQuery] = useState('');
  const [onlyChanges, setOnlyChanges] = useState(false);
  const baseline =
    scenarios.find(
      (scenario) => scenario.id === baselineId && scenario.id !== current.id,
    ) ?? scenarios.find((scenario) => scenario.id !== current.id);
  const rows = useMemo(
    () => (baseline ? compareScenarios(baseline, current, threshold) : []),
    [baseline, current, threshold],
  );
  if (!baseline)
    return (
      <section className="panel comparison-panel">
        <h2>Two scenarios make a comparison.</h2>
        <p>
          This report contains one scenario. Load a report with at least two
          scenarios, or restore the demo, to compare their results.
        </p>
      </section>
    );
  const visible = rows.filter(
    (row) =>
      row.name.toLowerCase().includes(query.trim().toLowerCase()) &&
      (!onlyChanges ||
        row.alertChange === 'new' ||
        row.alertChange === 'cleared'),
  );
  const alerts = (scenario: Scenario) =>
    scenario.drift.features.filter((feature) =>
      isAlert(
        feature,
        threshold,
        scenario.drift.config.alpha,
        scenario.drift.config.missing_threshold,
      ),
    ).length;
  const beforeAlerts = alerts(baseline);
  const afterAlerts = alerts(current);
  return (
    <section
      className="panel comparison-panel"
      aria-labelledby="comparison-heading"
    >
      <div className="comparison-heading">
        <div>
          <span className="eyebrow">SCENARIO COMPARISON</span>
          <h2 id="comparison-heading">What changed?</h2>
          <p>
            Compare <strong>{current.name}</strong> with another scenario in
            this report.
          </p>
        </div>
        <div className="comparison-baseline">
          <label htmlFor="comparison-baseline">Comparison baseline</label>
          <select
            id="comparison-baseline"
            value={baseline.id}
            onChange={(event) => setBaselineId(event.target.value)}
          >
            {scenarios
              .filter((scenario) => scenario.id !== current.id)
              .map((scenario) => (
                <option key={scenario.id} value={scenario.id}>
                  {scenario.name}
                </option>
              ))}
          </select>
        </div>
      </div>
      <p className="comparison-explanation">
        Deltas are selected scenario minus baseline. “pp” means percentage
        points; “—” means unavailable. Alerts use your PSI threshold (
        {threshold.toFixed(2)}) and each scenario’s saved significance and
        missingness thresholds.
      </p>
      <section
        className="comparison-table-scroll"
        tabIndex={0}
        aria-label="Scenario metrics comparison"
      >
        <table className="comparison-table">
          <caption>Performance and alert totals</caption>
          <thead>
            <tr>
              <th scope="col">Measure</th>
              <th scope="col">{baseline.name} (baseline)</th>
              <th scope="col">{current.name} (selected)</th>
              <th scope="col">Change</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <th scope="row">Accuracy</th>
              <td>{percent(baseline.metrics?.accuracy ?? null)}</td>
              <td>{percent(current.metrics?.accuracy ?? null)}</td>
              <td>
                {delta(
                  metricDelta(
                    current.metrics?.accuracy ?? null,
                    baseline.metrics?.accuracy ?? null,
                  ),
                  true,
                )}
              </td>
            </tr>
            <tr>
              <th scope="row">Macro F1</th>
              <td>{number(baseline.metrics?.macro_f1 ?? null)}</td>
              <td>{number(current.metrics?.macro_f1 ?? null)}</td>
              <td>
                {delta(
                  metricDelta(
                    current.metrics?.macro_f1 ?? null,
                    baseline.metrics?.macro_f1 ?? null,
                  ),
                )}
              </td>
            </tr>
            <tr>
              <th scope="row">Features flagged</th>
              <td>
                {beforeAlerts} / {baseline.drift.feature_count}
              </td>
              <td>
                {afterAlerts} / {current.drift.feature_count}
              </td>
              <td>{delta(afterAlerts - beforeAlerts).replace('.000', '')}</td>
            </tr>
          </tbody>
        </table>
      </section>
      <output className="comparison-summary">
        {rows.filter((row) => row.alertChange === 'new').length} new alerts ·{' '}
        {rows.filter((row) => row.alertChange === 'cleared').length} cleared
        alerts · {rows.filter((row) => row.alertChange === 'persistent').length}{' '}
        alerting in both
      </output>
      <div className="comparison-filters">
        <label>
          Search compared features
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Feature name"
          />
        </label>
        <label className="comparison-checkbox">
          <input
            type="checkbox"
            checked={onlyChanges}
            onChange={(event) => setOnlyChanges(event.target.checked)}
          />
          Only new or cleared alerts
        </label>
        <output>
          {visible.length} of {rows.length} features
        </output>
      </div>
      <section
        className="comparison-table-scroll"
        tabIndex={0}
        aria-label="Feature changes comparison"
      >
        <table className="comparison-table">
          <caption>
            Feature changes between {baseline.name} and {current.name}
          </caption>
          <thead>
            <tr>
              <th scope="col">Feature</th>
              <th scope="col">Baseline PSI</th>
              <th scope="col">Selected PSI</th>
              <th scope="col">PSI change</th>
              <th scope="col">Missingness change</th>
              <th scope="col">Alert change</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((row) => (
              <tr key={row.name}>
                <th scope="row">{row.name.replaceAll('_', ' ')}</th>
                <td>{number(row.baseline?.psi ?? null)}</td>
                <td>{number(row.current?.psi ?? null)}</td>
                <td>{delta(row.psiDelta)}</td>
                <td>{delta(row.missingDelta, true)}</td>
                <td>
                  <span className={`comparison-alert ${row.alertChange}`}>
                    {labels[row.alertChange]}
                  </span>
                </td>
              </tr>
            ))}
            {visible.length === 0 && (
              <tr>
                <td colSpan={6}>
                  No features match. Adjust your search or turn off the
                  alert-change filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
      <p className="comparison-explanation">
        Missingness change compares the fraction missing in each scenario’s
        current data. Features absent from either scenario are marked “Not
        comparable.” These comparisons describe the supplied samples; they do
        not establish why a model’s performance changed.
      </p>
    </section>
  );
}
