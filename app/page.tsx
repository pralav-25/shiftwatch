'use client';

import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { flushSync } from 'react-dom';
import planetArtwork from '@/assets/layered-sphere.png';
import {
  Activity,
  ArrowDownToLine,
  ArrowUpRight,
  Upload,
  FlaskConical,
  GitBranch,
  Layers3,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  TriangleAlert,
} from 'lucide-react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from '@/components/ui/select';
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/table';
import { Checkbox } from '@/components/ui/checkbox';
import source from '@/public/reports/demo.json';
import {
  type Report,
  type Feature,
  isAlert,
  withPsiThreshold,
  sortFeatures,
  parseReport,
} from '@/lib/report';

const demo = source as Report;
const pct = (value: number) => `${(value * 100).toFixed(1)}%`;
const num = (value: number | null, digits = 3) =>
  value === null ? '—' : value.toFixed(digits);
const pretty = (name: string) => name.replaceAll('_', ' ');

function Distribution({ feature }: { feature: Feature }) {
  const bins = feature.histogram;
  const max =
    Math.max(...bins.flatMap((b) => [b.reference, b.current]), 0.05) * 1.15;
  return (
    <figure className="distribution">
      <svg
        viewBox="0 0 720 260"
        aria-label={`Distribution of ${pretty(feature.name)} in reference and current data`}
      >
        <title>{`Observed-value distribution: ${pretty(feature.name)}`}</title>
        <desc>
          Reference mean {num(feature.reference_mean)}, current mean{' '}
          {num(feature.current_mean)}. Each bar shows the proportion of observed
          values in a bin.
        </desc>
        {[0, 1, 2, 3, 4].map((i) => (
          <g key={i}>
            <line
              x1="44"
              x2="706"
              y1={216 - i * 48}
              y2={216 - i * 48}
              stroke="var(--chart-grid)"
              strokeDasharray="3 5"
            />
            <text
              x="32"
              y={220 - i * 48}
              textAnchor="end"
              fill="var(--chart-label)"
              fontSize="12"
            >
              {Math.round(((max * i) / 4) * 100)}%
            </text>
          </g>
        ))}
        {bins.map((bin, i) => {
          const step = 650 / bins.length;
          return (
            <g key={i}>
              <rect
                x={50 + i * step}
                y={216 - (bin.reference / max) * 192}
                width={step * 0.37}
                height={(bin.reference / max) * 192}
                rx="2"
                fill="var(--chart-reference)"
              >
                <title>{`Reference: ${pct(bin.reference)}, ${num(bin.low, 2)} to ${num(bin.high, 2)}`}</title>
              </rect>
              <rect
                x={50 + i * step + step * 0.4}
                y={216 - (bin.current / max) * 192}
                width={step * 0.37}
                height={(bin.current / max) * 192}
                rx="2"
                fill="var(--chart-current)"
              >
                <title>{`Current: ${pct(bin.current)}, ${num(bin.low, 2)} to ${num(bin.high, 2)}`}</title>
              </rect>
              {i % 3 === 0 && (
                <text
                  x={50 + i * step}
                  y="244"
                  fill="var(--chart-label)"
                  fontSize="12"
                >
                  {num(bin.low, 1)}
                </text>
              )}
            </g>
          );
        })}
        {bins.length === 0 && (
          <text x="360" y="130" textAnchor="middle" fill="var(--chart-label)">
            Not enough observed data to plot
          </text>
        )}
      </svg>
      <figcaption>Equal-width display bins · observed values only</figcaption>
    </figure>
  );
}

export default function Home() {
  const [report, setReport] = useState<Report>(demo);
  const [importError, setImportError] = useState('');
  const [importing, setImporting] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const [scenarioId, setScenarioId] = useState('severe');
  const scenario =
    report.scenarios.find((s) => s.id === scenarioId) ?? report.scenarios[0];
  const [threshold, setThreshold] = useState(0.2);
  const [selected, setSelected] = useState('flavanoids');
  const [query, setQuery] = useState('');
  const [onlyAlerts, setOnlyAlerts] = useState(false);
  const config = scenario.drift.config;
  const features = useMemo(
    () =>
      sortFeatures(
        scenario.drift.features,
        query,
        onlyAlerts,
        threshold,
        config.alpha,
        config.missing_threshold,
      ),
    [scenario, query, onlyAlerts, threshold, config],
  );
  const feature =
    scenario.drift.features.find((f) => f.name === selected) ??
    scenario.drift.features[0];
  const flagged = scenario.drift.features.filter((f) =>
    isAlert(f, threshold, config.alpha, config.missing_threshold),
  );
  const metrics = scenario.metrics;
  const baseline = report.scenarios[0].metrics;
  const latest = useRef({ report, scenario, threshold });
  useLayoutEffect(() => {
    latest.current = { report, scenario, threshold };
  }, [report, scenario, threshold]);
  useEffect(() => {
    type Tool = {
      name: string;
      description: string;
      inputSchema: object;
      annotations: { readOnlyHint: boolean; untrustedContentHint: boolean };
      execute: (input: unknown) => unknown;
    };
    const context = (
      document as Document & {
        modelContext?: {
          registerTool: (
            tool: Tool,
            options: { signal: AbortSignal },
          ) => unknown;
        };
      }
    ).modelContext;
    if (!context?.registerTool) return;
    const lifecycle = new AbortController();
    const summary = () => {
      const { scenario: s, threshold: t } = latest.current;
      return {
        scenario: s.id,
        threshold: t,
        alerts: s.drift.features
          .filter((f) =>
            isAlert(
              f,
              t,
              s.drift.config.alpha,
              s.drift.config.missing_threshold,
            ),
          )
          .map((f) => ({ feature: f.name, psi: f.psi, q: f.q_value })),
        accuracy: s.metrics?.accuracy ?? null,
      };
    };
    const definitions: Tool[] = [
      {
        name: 'get_drift_summary',
        description:
          'Read the currently selected report, scenario, and drift alerts.',
        inputSchema: {
          type: 'object',
          properties: {},
          additionalProperties: false,
        },
        annotations: { readOnlyHint: true, untrustedContentHint: true },
        execute: () => summary(),
      },
      {
        name: 'select_drift_scenario',
        description:
          'Select an existing scenario in the visible dashboard and return its drift summary.',
        inputSchema: {
          type: 'object',
          properties: { scenarioId: { type: 'string' } },
          required: ['scenarioId'],
          additionalProperties: false,
        },
        annotations: { readOnlyHint: false, untrustedContentHint: true },
        execute: (input: unknown) => {
          const id =
            input && typeof input === 'object' && 'scenarioId' in input
              ? input.scenarioId
              : null;
          if (
            typeof id !== 'string' ||
            !latest.current.report.scenarios.some((s) => s.id === id)
          )
            throw new Error('Unknown scenario ID');
          flushSync(() => setScenarioId(id));
          return summary();
        },
      },
    ];
    for (const tool of definitions) {
      try {
        void Promise.resolve(
          context.registerTool(tool, { signal: lifecycle.signal }),
        ).catch(() => {});
      } catch {
        /* Optional browser capability; regular UI remains available. */
      }
    }
    return () => lifecycle.abort();
  }, []);
  async function loadReport(file?: File) {
    if (!file) return;
    setImportError('');
    setImporting(true);
    try {
      if (file.size > 5_000_000)
        throw new Error('Choose a report smaller than 5 MB.');
      const next = parseReport(JSON.parse(await file.text()));
      setReport(next);
      setScenarioId(next.scenarios[0].id);
      setThreshold(next.scenarios[0].drift.config.psi_threshold);
      setSelected(next.scenarios[0].drift.features[0].name);
      setQuery('');
      setOnlyAlerts(false);
    } catch (error) {
      setImportError(
        error instanceof SyntaxError
          ? 'This file is not valid JSON. Export a report with the Python CLI.'
          : error instanceof Error
            ? error.message
            : 'Could not read this report.',
      );
    } finally {
      setImporting(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  }
  function restoreDemo() {
    setReport(demo);
    setScenarioId('severe');
    setThreshold(0.2);
    setSelected('flavanoids');
    setQuery('');
    setOnlyAlerts(false);
    setImportError('');
  }
  function download() {
    const exported = withPsiThreshold(report, threshold);
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(exported, null, 2)], {
        type: 'application/json',
      }),
    );
    const link = document.createElement('a');
    link.href = url;
    link.download = 'shiftwatch-report.json';
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return (
    <>
      <a className="skip-link" href="#workspace">
        Skip to workspace
      </a>
      <header className="topbar">
        <a href="#workspace" className="brand">
          <span className="brand-symbol">S/</span>ShiftWatch
          <span className="version">v1.0</span>
        </a>
        <div className="top-links">
          <span className="local-indicator">
            <i /> Reproducible experiment
          </span>
          <a
            href="https://github.com/pralav-25/shiftwatch"
            target="_blank"
            rel="noreferrer"
          >
            View source <ArrowUpRight size={15} />
          </a>
        </div>
      </header>
      <main id="workspace" className="workspace">
        <div className="breadcrumb">
          <FlaskConical size={15} /> ML WORKSPACE <span>/</span>{' '}
          {report.dataset.name}
        </div>
        <section className="page-heading">
          <div className="heading-art" aria-hidden="true">
            {/* oxlint-disable-next-line nextjs/no-img-element -- Static decorative PNG; this export has no image-optimization server. */}
            <img
              src={
                typeof planetArtwork === 'string'
                  ? planetArtwork
                  : planetArtwork.src
              }
              alt=""
              width={1254}
              height={1254}
              className="heading-planet"
              loading="eager"
              decoding="async"
            />
          </div>
          <div className="heading-orbits" aria-hidden="true">
            <svg
              viewBox="0 0 800 350"
              fill="none"
              preserveAspectRatio="xMidYMid slice"
            >
              <ellipse
                cx="510"
                cy="154"
                rx="380"
                ry="122"
                transform="rotate(-17 510 154)"
                stroke="#21808d"
                strokeOpacity=".13"
                strokeWidth=".7"
              />
              <ellipse
                cx="518"
                cy="154"
                rx="322"
                ry="168"
                transform="rotate(20 518 154)"
                stroke="#b19164"
                strokeOpacity=".14"
                strokeWidth=".7"
              />
              <ellipse
                cx="530"
                cy="160"
                rx="460"
                ry="190"
                transform="rotate(-17 530 160)"
                stroke="#7a8e82"
                strokeOpacity=".09"
                strokeWidth=".7"
              />
            </svg>
          </div>
          <div className="page-heading-copy">
            <div className="eyebrow">DATA DRIFT & MODEL EVALUATION</div>
            <h1>
              Model monitoring<span className="title-dot">.</span>
            </h1>
            <p>
              Trace a distribution shift. Understand its impact on your model.
            </p>
          </div>
          <div className="heading-actions">
            <input
              ref={inputRef}
              type="file"
              accept="application/json,.json"
              className="sr-only"
              aria-label="Load ShiftWatch JSON report"
              onChange={(e) => void loadReport(e.target.files?.[0])}
            />
            <button
              className="button secondary"
              disabled={importing}
              onClick={() => inputRef.current?.click()}
            >
              <Upload size={16} />
              {importing ? 'Reading…' : 'Load report'}
            </button>
            <button className="button capsule" onClick={download}>
              <span className="button-disc">
                <ArrowDownToLine size={16} />
              </span>{' '}
              Export report
            </button>
          </div>
        </section>
        {importError && (
          <p role="alert" className="import-error">
            {importError}
          </p>
        )}
        {report !== demo && (
          <div className="import-note">
            <span>Imported report · processed only in this browser</span>
            <button onClick={restoreDemo}>Restore demo</button>
          </div>
        )}
        <div className="run-bar">
          <div className="run-name">
            <GitBranch size={17} />
            <strong>{report.dataset.name}</strong>
            <span className="badge neutral">
              {report.kind === 'experiment'
                ? 'Classification'
                : 'Dataset comparison'}
            </span>
          </div>
          <div className="run-meta">
            <span>{report.selected_model ?? 'No model attached'}</span>
            <span>Seed {report.seed ?? '—'}</span>
            <span>
              {scenario.drift.reference_rows} reference /{' '}
              {scenario.drift.current_rows} current
            </span>
          </div>
        </div>
        <div className="scenario-bar">
          <div className="field-group">
            <label id="scenario-label" htmlFor="scenario-select">
              Experiment scenario
            </label>
            <Select
              value={scenario.id}
              onValueChange={(v) => v && setScenarioId(v)}
            >
              <SelectTrigger
                id="scenario-select"
                aria-labelledby="scenario-label"
                className="scenario-select"
              >
                <SelectValue>{scenario.name}</SelectValue>
              </SelectTrigger>
              <SelectContent>
                {report.scenarios.map((s) => (
                  <SelectItem key={s.id} value={s.id}>
                    {s.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <span className="badge neutral">
              {scenario.synthetic ? 'Simulated shift' : 'Observed data'}
            </span>
          </div>
          <div className="field-group threshold">
            <SlidersHorizontal size={15} />
            <label id="threshold-label" htmlFor="threshold-select">
              PSI threshold
            </label>
            <Select
              value={String(threshold)}
              onValueChange={(v) => v && setThreshold(Number(v))}
            >
              <SelectTrigger
                id="threshold-select"
                aria-labelledby="threshold-label"
              >
                <SelectValue>{threshold.toFixed(2)}</SelectValue>
              </SelectTrigger>
              <SelectContent>
                {[...new Set([0.1, 0.2, 0.3, config.psi_threshold])]
                  .sort((a, b) => a - b)
                  .map((t) => (
                    <SelectItem key={t} value={String(t)}>
                      {t.toFixed(2)}
                    </SelectItem>
                  ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <p className="scenario-note">{scenario.description}</p>
        <section className="stats-grid" aria-label="Scenario metrics">
          <div className="stat">
            <div className="stat-label">
              Features flagged <Activity size={16} />
            </div>
            <div className="stat-value amber">
              {flagged.length}
              <small>/ {scenario.drift.feature_count}</small>
            </div>
            <span className="stat-detail">
              Distribution or missingness alerts
            </span>
          </div>
          <div className="stat">
            <div className="stat-label">
              Model accuracy <ShieldCheck size={16} />
            </div>
            <div className="stat-value">
              {metrics ? pct(metrics.accuracy) : '—'}
            </div>
            <span className="stat-detail">
              {metrics && baseline
                ? `${((metrics.accuracy - baseline.accuracy) * 100).toFixed(1)} pp vs untouched holdout`
                : 'Labels required for evaluation'}
            </span>
          </div>
          <div className="stat">
            <div className="stat-label">
              Macro F1 <Layers3 size={16} />
            </div>
            <div className="stat-value">
              {metrics ? num(metrics.macro_f1) : '—'}
            </div>
            <span className="stat-detail">Equal weight across classes</span>
          </div>
          <div className="stat">
            <div className="stat-label">
              Current observations <FlaskConical size={16} />
            </div>
            <div className="stat-value">{scenario.drift.current_rows}</div>
            <span className="stat-detail">
              {scenario.synthetic
                ? 'Perturbed test rows · original labels'
                : 'Independent comparison batch'}
            </span>
          </div>
        </section>
        <Tabs defaultValue="drift" className="main-tabs">
          <TabsList variant="line" className="tab-list">
            <TabsTrigger value="drift">Data drift</TabsTrigger>
            <TabsTrigger value="evaluation">Model evaluation</TabsTrigger>
            <TabsTrigger value="method">Methodology</TabsTrigger>
          </TabsList>
          <TabsContent value="drift">
            <div className="analysis-grid">
              <section className="panel chart-panel">
                <div className="panel-heading">
                  <div>
                    <span className="eyebrow">FEATURE DISTRIBUTION</span>
                    <h2>{pretty(feature.name)}</h2>
                  </div>
                  <div className="legend">
                    <span>
                      <i className="reference-key" />
                      Reference
                    </span>
                    <span>
                      <i className="current-key" />
                      Current
                    </span>
                  </div>
                </div>
                <Distribution feature={feature} />
                <div className="chart-footer">
                  <span>
                    Reference mean{' '}
                    <strong>{num(feature.reference_mean, 2)}</strong>
                  </span>
                  <span>
                    Current mean <strong>{num(feature.current_mean, 2)}</strong>
                  </span>
                  <span>
                    KS statistic <strong>{num(feature.ks)}</strong>
                  </span>
                </div>
              </section>
              <aside className="panel insight-panel">
                <span className="eyebrow">SIGNAL SUMMARY</span>
                <div
                  className={`signal-icon ${flagged.length ? 'warn' : 'ok'}`}
                >
                  {flagged.length ? (
                    <TriangleAlert size={23} />
                  ) : (
                    <ShieldCheck size={23} />
                  )}
                </div>
                <h2>
                  {flagged.length
                    ? 'A shift worth investigating'
                    : 'No alerts at this threshold'}
                </h2>
                <p>
                  {flagged.length
                    ? `${flagged.length} of ${scenario.drift.feature_count} features cross the configured alert rules. Inspect their distributions before deciding to retrain.`
                    : 'These checks found no qualifying change. This does not prove that the model or data is healthy.'}
                </p>
                <div className="rule">
                  <span>Distribution rule</span>
                  <strong>
                    PSI ≥ {threshold.toFixed(2)} & q ≤ {config.alpha}
                  </strong>
                </div>
                <div className="rule">
                  <span>Missingness rule</span>
                  <strong>
                    Absolute change ≥ {pct(config.missing_threshold)}
                  </strong>
                </div>
                <div className="insight-foot">
                  Drift is a signal, not proof of model failure.
                </div>
              </aside>
            </div>
            <section className="panel feature-panel">
              <div className="panel-heading">
                <div>
                  <h2>
                    Feature diagnostics{' '}
                    <span className="count">
                      {scenario.drift.feature_count}
                    </span>
                  </h2>
                  <p>Select a feature to inspect its distribution.</p>
                </div>
                <div className="table-controls">
                  <label className="search">
                    <Search size={15} />
                    <input
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder="Find a feature…"
                      aria-label="Find a feature"
                    />
                  </label>
                  <label className="checkbox-label">
                    <Checkbox
                      checked={onlyAlerts}
                      onCheckedChange={(v) => setOnlyAlerts(v === true)}
                    />{' '}
                    Alerts only
                  </label>
                </div>
              </div>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Feature</TableHead>
                    <TableHead>PSI ↓</TableHead>
                    <TableHead>KS q-value</TableHead>
                    <TableHead>Missing (current)</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {features.map((f) => (
                    <TableRow
                      key={f.name}
                      className={feature.name === f.name ? 'selected-row' : ''}
                    >
                      <TableCell>
                        <button
                          className="feature-name"
                          onClick={() => setSelected(f.name)}
                          aria-pressed={feature.name === f.name}
                        >
                          {pretty(f.name)}
                          <ArrowUpRight size={13} />
                        </button>
                      </TableCell>
                      <TableCell className="mono">
                        <span className="psi-cell">
                          {num(f.psi)}
                          <i
                            style={{
                              width: `${(Math.min(f.psi ?? 0, 2) / 2) * 54}px`,
                            }}
                          />
                        </span>
                      </TableCell>
                      <TableCell className="mono">
                        {f.q_value === null
                          ? '—'
                          : f.q_value < 0.001
                            ? '< 0.001'
                            : num(f.q_value)}
                      </TableCell>
                      <TableCell className="mono">
                        {pct(f.current_missing)}
                      </TableCell>
                      <TableCell>
                        <span
                          className={`badge ${isAlert(f, threshold, config.alpha, config.missing_threshold) ? 'warning' : 'good'}`}
                        >
                          {isAlert(
                            f,
                            threshold,
                            config.alpha,
                            config.missing_threshold,
                          )
                            ? 'Alert'
                            : f.insufficient_data
                              ? 'Insufficient data'
                              : 'No alert'}
                        </span>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              {features.length === 0 && (
                <div className="empty-state">
                  No features match these filters. Clear the search or turn off
                  “Alerts only”.
                </div>
              )}
              <div className="table-foot">
                {features.length} features shown · BH-adjusted KS p-values ·
                threshold changes are exploratory
              </div>
            </section>
          </TabsContent>
          <TabsContent value="evaluation">
            <section className="panel prose">
              <h2>Model selection</h2>
              <p>
                The highest mean macro F1 across five training folds selects the
                model. Preprocessing is fitted separately inside every fold. The
                test set is reserved for final evaluation.
              </p>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Candidate</TableHead>
                    <TableHead>CV macro F1</TableHead>
                    <TableHead>Fold standard deviation</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {report.models.map((m) => (
                    <TableRow key={m.name}>
                      <TableCell>
                        {m.name}{' '}
                        {report.selected_model === m.name && (
                          <span className="badge good">Selected</span>
                        )}
                      </TableCell>
                      <TableCell>{num(m.cv_mean)}</TableCell>
                      <TableCell>{num(m.cv_std)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              {report.models.length === 0 && (
                <p>No trained model is attached to this CSV comparison.</p>
              )}
              {metrics && (
                <>
                  <h2>Current scenario evaluation</h2>
                  <p>
                    Accuracy: {pct(metrics.accuracy)} · Bootstrap 95% interval:{' '}
                    {pct(metrics.accuracy_ci[0])}–{pct(metrics.accuracy_ci[1])}{' '}
                    · Log loss: {num(metrics.log_loss)}
                  </p>
                  <p>
                    This interval captures test-sample uncertainty for this
                    fitted model, not uncertainty from retraining.
                  </p>
                  <h3>Confusion matrix</h3>
                  <p>Rows = actual class · columns = predicted class</p>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Actual / predicted</TableHead>
                        {metrics.class_labels.map((l) => (
                          <TableHead key={l}>{l}</TableHead>
                        ))}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {metrics.confusion_matrix.map((row, i) => (
                        <TableRow key={i}>
                          <TableCell>{metrics.class_labels[i]}</TableCell>
                          {row.map((n, j) => (
                            <TableCell key={j}>
                              <span
                                className={`matrix-cell ${i === j ? 'diagonal' : ''}`}
                              >
                                {n}
                              </span>
                            </TableCell>
                          ))}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </>
              )}
            </section>
          </TabsContent>
          <TabsContent value="method">
            <section className="panel prose">
              <span className="eyebrow">REPRODUCIBLE BY DESIGN</span>
              <h2>From training data to a drift report</h2>
              <div className="pipeline">
                <span>01 · Stratified split</span>
                <span>02 · Cross-validation</span>
                <span>03 · Held-out evaluation</span>
                <span>04 · Drift analysis</span>
              </div>
              <h3>How the alerts work</h3>
              <p>
                Population Stability Index (PSI) measures changes in
                reference-quantile bins with 0.5-count smoothing. A two-sample
                Kolmogorov–Smirnov test compares the observed distributions;
                Benjamini–Hochberg adjusts its p-values across tested features.
                Both the PSI threshold and adjusted q-value rule must pass.
                Missingness is checked separately.
              </p>
              <h3>What this experiment can tell you</h3>
              <p>
                The bundled demo uses UCI Wine; imported CSV reports use your
                own numerical features.
              </p>
              <p>
                The bundled UCI Wine dataset has 178 samples, 13 numerical
                features, and three classes. The fixed 70/30 split leaves 124
                training rows and 54 test rows. The shifted scenarios modify the
                same test rows while retaining their original labels. They are
                controlled stress tests, not observations of production drift.
              </p>
              <h3>Limits to keep in mind</h3>
              <p>
                Small samples produce noisy estimates. KS assumes independent
                continuous observations, and rounding or ties affect
                calibration. Univariate checks can miss joint distribution
                changes or concept drift. Thresholds need calibration to your
                own data and alert budget. No model automatically retrains.
              </p>
              <h3>Reproduce or use your own data</h3>
              <pre>
                <code>
                  pip install -e &apos;.[dev]&apos;{'\n'}shiftwatch demo{'\n'}
                  shiftwatch compare reference.csv current.csv --output
                  report.json
                </code>
              </pre>
              <p>
                The dashboard displays exported Python results. It does not
                train a model in your browser. Use “Load report” to explore the
                JSON produced by either command. Files are read locally and are
                not sent to a server.
              </p>
              <a
                className="text-link"
                href="https://github.com/pralav-25/shiftwatch#readme"
                target="_blank"
                rel="noreferrer"
              >
                Read the full project documentation <ArrowUpRight size={15} />
              </a>
            </section>
          </TabsContent>
        </Tabs>
        <footer>
          <span>
            <span className="footer-mark">S/</span> ShiftWatch · ML monitoring
            workbench
          </span>
          <span>
            Python analysis. Reproducible evidence.{' '}
            <a
              href="https://archive.ics.uci.edu/dataset/109/wine"
              target="_blank"
              rel="noreferrer"
            >
              UCI Wine ↗
            </a>
          </span>
        </footer>
      </main>
    </>
  );
}
