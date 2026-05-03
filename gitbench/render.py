"""HTML report renderer for GitBench results."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def load_runs_from_dir(directory: str) -> list[dict]:
    """Load all run envelope JSON files from a directory.

    Args:
        directory: Path to directory containing JSON run files.

    Returns:
        List of run envelope dicts, sorted by timestamp.
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")

    runs = []
    for f in sorted(dir_path.glob("*.json")):
        try:
            data = json.loads(f.read_text())
            if "version" in data and "results" in data:
                runs.append(data)
        except (json.JSONDecodeError, KeyError):
            continue

    runs.sort(key=lambda r: r.get("timestamp", ""))
    return runs


def load_runs_from_jsonl(path: str) -> list[dict]:
    """Load run envelopes from a JSONL file.

    Args:
        path: Path to JSONL file.

    Returns:
        List of run envelope dicts, sorted by timestamp.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    runs = []
    for line in file_path.read_text().strip().split("\n"):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
            if "version" in data and "results" in data:
                runs.append(data)
        except (json.JSONDecodeError, KeyError):
            continue

    runs.sort(key=lambda r: r.get("timestamp", ""))
    return runs


def aggregate_runs(runs: list[dict]) -> dict[str, Any]:
    """Aggregate multiple runs into a structured summary for rendering.

    Args:
        runs: List of run envelope dicts.

    Returns:
        Dict with:
        - models: list of model names
        - benchmarks: list of benchmark names
        - model_summaries: {model: {total_runs, total_fixtures, total_passed, pass_at_k}}
        - matrix: {model: {benchmark: {pass_at_k, total, passed, avg_similarity}}}
        - fixtures: {model: {benchmark: [{fixture_id, passed, similarity, error}]}}
        - runs_meta: [{timestamp, model, profile, git_sha}]
    """
    models_set: set[str] = set()
    benchmarks_set: set[str] = set()
    model_data: dict[str, dict] = {}

    for run in runs:
        model = run["model"]
        models_set.add(model)

        if model not in model_data:
            model_data[model] = {
                "total_runs": 0,
                "total_fixtures": 0,
                "total_passed": 0,
                "benchmarks": {},
            }

        model_data[model]["total_runs"] += 1

        for result in run.get("results", []):
            if "error" in result and "benchmark" not in result:
                continue

            bench = result.get("benchmark", "unknown")
            benchmarks_set.add(bench)

            if bench not in model_data[model]["benchmarks"]:
                model_data[model]["benchmarks"][bench] = {
                    "total": 0,
                    "passed": 0,
                    "scores": [],
                    "fixtures": [],
                }

            bd = model_data[model]["benchmarks"][bench]
            bd["total"] += result.get("total", 0)
            bd["passed"] += result.get("passed", 0)

            for score in result.get("scores", []):
                bd["scores"].append(score.get("similarity", 0))
                bd["fixtures"].append({
                    "fixture_id": score.get("fixture_id", "?"),
                    "passed": score.get("passed", False),
                    "similarity": score.get("similarity", 0),
                    "error": score.get("error"),
                    "model_output": score.get("model_output", "")[:200],
                })

    # Build summaries and matrix
    model_summaries = {}
    matrix = {}
    fixtures = {}

    for model, data in model_data.items():
        model_summaries[model] = {
            "total_runs": data["total_runs"],
            "total_fixtures": data["total_fixtures"],
            "total_passed": data["total_passed"],
            "pass_at_k": round(
                data["total_passed"] / data["total_fixtures"], 4
            ) if data["total_fixtures"] > 0 else 0.0,
        }

        matrix[model] = {}
        fixtures[model] = {}

        for bench, bd in data["benchmarks"].items():
            avg_sim = round(sum(bd["scores"]) / len(bd["scores"]), 4) if bd["scores"] else 0.0
            matrix[model][bench] = {
                "pass_at_k": round(bd["passed"] / bd["total"], 4) if bd["total"] > 0 else 0.0,
                "total": bd["total"],
                "passed": bd["passed"],
                "avg_similarity": avg_sim,
            }
            fixtures[model][bench] = bd["fixtures"]

            # Roll up to model summary
            model_summaries[model]["total_fixtures"] += bd["total"]
            model_summaries[model]["total_passed"] += bd["passed"]

        # Recompute pass_at_k after rollup
        sf = model_summaries[model]
        sf["pass_at_k"] = round(
            sf["total_passed"] / sf["total_fixtures"], 4
        ) if sf["total_fixtures"] > 0 else 0.0

    runs_meta = []
    for run in runs:
        runs_meta.append({
            "timestamp": run.get("timestamp", ""),
            "model": run.get("model", ""),
            "profile": run.get("profile", ""),
            "git_sha": run.get("git_sha", ""),
        })

    return {
        "models": sorted(models_set),
        "benchmarks": sorted(benchmarks_set),
        "model_summaries": model_summaries,
        "matrix": matrix,
        "fixtures": fixtures,
        "runs_meta": runs_meta,
    }


def render_html(data: dict[str, Any], title: str = "GitBench Report") -> str:
    """Render aggregated data as a self-contained HTML report.

    Args:
        data: Aggregated data from aggregate_runs().
        title: HTML page title.

    Returns:
        Complete HTML string.
    """
    models = data["models"]
    benchmarks = data["benchmarks"]
    matrix = data["matrix"]
    model_summaries = data["model_summaries"]
    fixtures = data["fixtures"]

    # Prepare chart data
    summary_labels = json.dumps(models)
    summary_values = json.dumps([round(model_summaries[m]["pass_at_k"] * 100, 1) for m in models])

    # Per-benchmark grouped bar data
    bench_datasets = []
    colors = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899"]
    for i, model in enumerate(models):
        values = []
        for bench in benchmarks:
            cell = matrix.get(model, {}).get(bench, {})
            values.append(round(cell.get("pass_at_k", 0) * 100, 1))
        bench_datasets.append({
            "label": model,
            "data": values,
            "backgroundColor": colors[i % len(colors)],
        })
    bench_datasets_json = json.dumps(bench_datasets)
    bench_labels_json = json.dumps(benchmarks)

    # Similarity data per model/benchmark
    sim_data = {}
    for model in models:
        sim_data[model] = {}
        for bench in benchmarks:
            fl = fixtures.get(model, {}).get(bench, [])
            sim_data[model][bench] = [
                {"id": f["fixture_id"], "sim": round(f["similarity"] * 100, 1), "passed": f["passed"]}
                for f in fl
            ]
    sim_data_json = json.dumps(sim_data)

    # Runs metadata
    runs_meta_json = json.dumps(data["runs_meta"])

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&family=DM+Mono:ital,wght@0,300;0,400;0,500;1,300&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
  :root {{
    --bg: #07090f;
    --surface: #0d1117;
    --card: #0f1520;
    --card-hover: #141d2e;
    --border: rgba(255,255,255,0.07);
    --border-accent: rgba(6,182,212,0.35);
    --text: #e8f0ff;
    --text-dim: #5a6a88;
    --text-mid: #8898b8;
    --accent: #06b6d4;
    --accent-glow: rgba(6,182,212,0.12);
    --pass: #10b981;
    --pass-bg: rgba(16,185,129,0.12);
    --pass-border: rgba(16,185,129,0.35);
    --warn: #f59e0b;
    --warn-bg: rgba(245,158,11,0.12);
    --warn-border: rgba(245,158,11,0.35);
    --fail: #f43f5e;
    --fail-bg: rgba(244,63,94,0.12);
    --fail-border: rgba(244,63,94,0.3);
    --font-display: 'Manrope', sans-serif;
    --font-mono: 'DM Mono', monospace;
  }}

  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  html {{ scroll-behavior: smooth; }}

  body {{
    font-family: var(--font-display);
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    line-height: 1.6;
    background-image:
      radial-gradient(ellipse 70% 40% at 60% -10%, rgba(6,182,212,0.07), transparent),
      radial-gradient(ellipse 50% 60% at -10% 80%, rgba(16,185,129,0.05), transparent);
  }}

  body::before {{
    content: '';
    position: fixed;
    inset: 0;
    background-image: radial-gradient(circle, rgba(255,255,255,0.045) 1px, transparent 1px);
    background-size: 32px 32px;
    pointer-events: none;
    z-index: 0;
  }}

  .page-wrapper {{
    position: relative;
    z-index: 1;
    max-width: 1440px;
    margin: 0 auto;
  }}

  /* ── HEADER ── */
  .header {{
    padding: 3rem 3.5rem 2.5rem;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 2rem;
    flex-wrap: wrap;
  }}

  .header-eyebrow {{
    font-family: var(--font-mono);
    font-size: 0.65rem;
    letter-spacing: 0.22em;
    color: var(--accent);
    text-transform: uppercase;
    margin-bottom: 0.6rem;
    opacity: 0.8;
  }}

  h1 {{
    font-size: clamp(2.2rem, 4vw, 3.2rem);
    font-weight: 800;
    letter-spacing: -0.03em;
    line-height: 1;
    color: var(--text);
  }}

  h1 .accent {{ color: var(--accent); }}

  .header-badges {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-top: 1.25rem;
  }}

  .badge {{
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.28rem 0.8rem;
    background: rgba(255,255,255,0.04);
    border: 1px solid var(--border);
    border-radius: 100px;
    font-family: var(--font-mono);
    font-size: 0.7rem;
    color: var(--text-mid);
    letter-spacing: 0.04em;
  }}

  .badge-pulse {{
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: var(--accent);
    box-shadow: 0 0 8px var(--accent);
    animation: pulse 2s ease-in-out infinite;
  }}

  @keyframes pulse {{
    0%, 100% {{ opacity: 1; box-shadow: 0 0 8px var(--accent); }}
    50% {{ opacity: 0.5; box-shadow: 0 0 4px var(--accent); }}
  }}

  /* ── MAIN LAYOUT ── */
  .main {{
    padding: 3rem 3.5rem;
    display: flex;
    flex-direction: column;
    gap: 3rem;
  }}

  /* ── SECTION LABELS ── */
  .section-label {{
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 1.5rem;
  }}

  .section-label span {{
    font-family: var(--font-mono);
    font-size: 0.65rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--text-dim);
  }}

  .section-label::after {{
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(to right, var(--border), transparent);
  }}

  /* ── SUMMARY CARDS ── */
  .summary-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(175px, 1fr));
    gap: 1rem;
  }}

  .summary-card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1.4rem 1.3rem 1.1rem;
    position: relative;
    overflow: hidden;
    transition: border-color 0.25s ease, box-shadow 0.25s ease, transform 0.25s ease;
    cursor: default;
    animation: fadeUp 0.5s ease backwards;
  }}

  .summary-card:hover {{
    transform: translateY(-3px);
    border-color: var(--border-accent);
    box-shadow: 0 8px 32px rgba(6,182,212,0.08), 0 0 0 1px rgba(6,182,212,0.1);
  }}

  .summary-card::after {{
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: var(--_bar-color, var(--border));
    opacity: 0.9;
  }}

  .card-eyebrow {{
    font-family: var(--font-mono);
    font-size: 0.65rem;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-bottom: 0.6rem;
  }}

  .card-value {{
    font-size: 2.6rem;
    font-weight: 800;
    letter-spacing: -0.04em;
    line-height: 1;
  }}

  .card-value.high {{ color: var(--pass); }}
  .card-value.mid {{ color: var(--warn); }}
  .card-value.low {{ color: var(--fail); }}

  .card-sub {{
    font-family: var(--font-mono);
    font-size: 0.68rem;
    color: var(--text-dim);
    margin-top: 0.55rem;
    letter-spacing: 0.03em;
  }}

  /* ── CHARTS ── */
  .charts-row {{
    display: grid;
    grid-template-columns: 1fr;
    gap: 1.25rem;
  }}

  .chart-card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1.75rem;
  }}

  .chart-label {{
    font-family: var(--font-mono);
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: var(--text-dim);
    margin-bottom: 1.5rem;
  }}

  canvas {{ max-height: 340px; }}

  /* ── MATRIX ── */
  .matrix-card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 14px;
    overflow: hidden;
  }}

  .matrix-inner {{
    overflow-x: auto;
    padding: 1.75rem;
  }}

  table {{
    width: 100%;
    border-collapse: collapse;
  }}

  th {{
    font-family: var(--font-mono);
    font-size: 0.63rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-dim);
    padding: 0.55rem 0.9rem;
    text-align: left;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
    font-weight: 400;
  }}

  td {{
    padding: 0.5rem 0.9rem;
    border-bottom: 1px solid rgba(255,255,255,0.03);
    white-space: nowrap;
    vertical-align: middle;
  }}

  tr:last-child td {{ border-bottom: none; }}

  tr:hover td {{ background: rgba(255,255,255,0.015); }}

  .bench-name {{
    font-family: var(--font-mono);
    font-size: 0.75rem;
    color: var(--text-mid);
    font-weight: 300;
  }}

  .heat-pill {{
    display: inline-flex;
    align-items: center;
    padding: 0.18rem 0.55rem;
    border-radius: 5px;
    font-family: var(--font-mono);
    font-size: 0.75rem;
    font-weight: 500;
    letter-spacing: 0.02em;
  }}

  .cell-count {{
    font-family: var(--font-mono);
    font-size: 0.65rem;
    color: var(--text-dim);
    margin-left: 0.3rem;
    letter-spacing: 0.02em;
  }}

  .heat-na {{
    font-family: var(--font-mono);
    font-size: 0.75rem;
    color: var(--text-dim);
    opacity: 0.5;
  }}

  /* ── FIXTURE ACCORDION ── */
  .fixture-list {{
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
  }}

  details.fx-model {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 14px;
    overflow: hidden;
    transition: border-color 0.2s;
  }}

  details.fx-model[open] {{
    border-color: rgba(6,182,212,0.2);
  }}

  summary.fx-summary {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1.1rem 1.5rem;
    cursor: pointer;
    list-style: none;
    user-select: none;
    transition: background 0.15s;
  }}

  summary.fx-summary::-webkit-details-marker {{ display: none; }}
  summary.fx-summary::marker {{ display: none; }}
  summary.fx-summary:hover {{ background: rgba(255,255,255,0.02); }}

  .fx-model-name {{
    font-size: 0.88rem;
    font-weight: 700;
    letter-spacing: -0.01em;
  }}

  .fx-right {{
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }}

  .fx-chevron {{
    width: 22px;
    height: 22px;
    border: 1px solid var(--border);
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-dim);
    font-size: 0.75rem;
    font-family: var(--font-mono);
    transition: all 0.2s;
    flex-shrink: 0;
  }}

  details.fx-model[open] .fx-chevron {{
    background: var(--accent-glow);
    border-color: var(--accent);
    color: var(--accent);
    transform: rotate(45deg);
  }}

  .fx-body {{
    padding: 0 1.5rem 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
  }}

  .fx-bench-header {{
    font-family: var(--font-mono);
    font-size: 0.62rem;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: var(--accent);
    padding-bottom: 0.45rem;
    border-bottom: 1px solid rgba(6,182,212,0.15);
    margin-bottom: 0.1rem;
    opacity: 0.75;
  }}

  .fx-row {{
    display: grid;
    grid-template-columns: 1fr auto auto;
    gap: 1rem;
    align-items: center;
    padding: 0.38rem 0;
    border-bottom: 1px solid rgba(255,255,255,0.03);
  }}

  .fx-row:last-child {{ border-bottom: none; }}

  .fx-id {{
    font-family: var(--font-mono);
    font-size: 0.75rem;
    color: var(--text-mid);
    font-weight: 300;
  }}

  .fx-sim {{
    font-family: var(--font-mono);
    font-size: 0.73rem;
    color: var(--text-dim);
    text-align: right;
  }}

  .result-pill {{
    font-family: var(--font-mono);
    font-size: 0.62rem;
    font-weight: 500;
    letter-spacing: 0.08em;
    padding: 0.18rem 0.55rem;
    border-radius: 4px;
    min-width: 42px;
    text-align: center;
  }}

  .result-pill.pass {{
    background: var(--pass-bg);
    color: var(--pass);
    border: 1px solid var(--pass-border);
  }}

  .result-pill.fail {{
    background: var(--fail-bg);
    color: var(--fail);
    border: 1px solid var(--fail-border);
  }}

  /* ── RUN HISTORY ── */
  .runs-card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 14px;
    overflow: hidden;
    padding: 1.75rem;
  }}

  .runs-card table th {{ font-weight: 400; }}

  .runs-card table td {{
    font-family: var(--font-mono);
    font-size: 0.77rem;
    color: var(--text-mid);
  }}

  .sha-text {{
    color: var(--accent);
    opacity: 0.6;
  }}

  /* ── FOOTER ── */
  .footer {{
    padding: 1.5rem 3.5rem;
    border-top: 1px solid var(--border);
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.75rem;
  }}

  .footer span {{
    font-family: var(--font-mono);
    font-size: 0.65rem;
    color: var(--text-dim);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    opacity: 0.6;
  }}

  /* ── ANIMATIONS ── */
  @keyframes fadeUp {{
    from {{ opacity: 0; transform: translateY(10px); }}
    to {{ opacity: 1; transform: translateY(0); }}
  }}

  /* ── RESPONSIVE ── */
  @media (max-width: 960px) {{
    .header {{ padding: 2rem 1.75rem 1.75rem; }}
    .main {{ padding: 2rem 1.75rem; }}
    .charts-row {{ grid-template-columns: 1fr; }}
    .footer {{ padding: 1.25rem 1.75rem; }}
  }}

  @media (max-width: 600px) {{
    .header {{ padding: 1.5rem 1.25rem 1.25rem; }}
    .main {{ padding: 1.5rem 1.25rem; }}
  }}
</style>
</head>
<body>
<div class="page-wrapper">

  <header class="header">
    <div>
      <div class="header-eyebrow">// benchmark report</div>
      <h1>{title}</h1>
      <div class="header-badges">
        <span class="badge"><span class="badge-pulse"></span>Generated {generated}</span>
        <span class="badge">{len(data['runs_meta'])} run(s)</span>
        <span class="badge">{len(models)} model(s)</span>
        <span class="badge">{len(benchmarks)} benchmark(s)</span>
      </div>
    </div>
  </header>

  <main class="main">

    <!-- Summary Cards -->
    <section>
      <div class="section-label"><span>Model Summary</span></div>
      <div class="summary-grid" id="summary-cards"></div>
    </section>

    <!-- Charts -->
    <section>
      <div class="section-label"><span>Performance Charts</span></div>
      <div class="charts-row">
        <div class="chart-card">
          <div class="chart-label">Per-Benchmark Comparison</div>
          <canvas id="benchChart"></canvas>
        </div>
      </div>
    </section>

    <!-- Matrix -->
    <section>
      <div class="section-label"><span>Results Matrix</span></div>
      <div class="matrix-card">
        <div class="matrix-inner">
          <table id="matrix-table">
            <thead><tr id="matrix-header"></tr></thead>
            <tbody id="matrix-body"></tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- Fixture Details -->
    <section>
      <div class="section-label"><span>Fixture Details</span></div>
      <div class="fixture-list" id="fixture-details"></div>
    </section>

    <!-- Run History -->
    <section>
      <div class="section-label"><span>Run History</span></div>
      <div class="runs-card">
        <table>
          <thead>
            <tr>
              <th>Timestamp</th><th>Model</th><th>Profile</th><th>Git SHA</th>
            </tr>
          </thead>
          <tbody id="runs-body"></tbody>
        </table>
      </div>
    </section>

  </main>

  <footer class="footer">
    <span>GitBench &mdash; Automated Git Task Benchmark</span>
    <span>{generated}</span>
  </footer>

</div>
<script>
const models = {summary_labels};
const benchmarks = {bench_labels_json};
const summaryValues = {summary_values};
const benchDatasets = {bench_datasets_json};
const simData = {sim_data_json};
const matrix = {json.dumps(matrix)};
const runsMeta = {runs_meta_json};
const modelSummaries = {json.dumps(model_summaries)};

function heatStyle(ratio) {{
  if (ratio >= 0.8) return {{ bg: 'var(--pass-bg)', color: 'var(--pass)', border: 'var(--pass-border)' }};
  if (ratio >= 0.5) return {{ bg: 'var(--warn-bg)', color: 'var(--warn)', border: 'var(--warn-border)' }};
  return {{ bg: 'var(--fail-bg)', color: 'var(--fail)', border: 'var(--fail-border)' }};
}}

// Summary cards
const cardsEl = document.getElementById('summary-cards');
models.forEach((m, i) => {{
  const s = modelSummaries[m];
  const pct = (s.pass_at_k * 100).toFixed(1);
  const cls = s.pass_at_k >= 0.8 ? 'high' : s.pass_at_k < 0.5 ? 'low' : 'mid';
  const barColor = s.pass_at_k >= 0.8 ? 'var(--pass)' : s.pass_at_k < 0.5 ? 'var(--fail)' : 'var(--warn)';
  cardsEl.innerHTML += `
    <div class="summary-card" style="animation-delay:${{i * 55}}ms;--_bar-color:${{barColor}}">
      <div class="card-eyebrow">${{m}}</div>
      <div class="card-value ${{cls}}">${{pct}}%</div>
      <div class="card-sub">${{s.total_passed}} / ${{s.total_fixtures}} fixtures</div>
    </div>`;
}});

// Chart global defaults
Chart.defaults.color = '#5a6a88';
Chart.defaults.font.family = "'DM Mono', monospace";
Chart.defaults.font.size = 11;

// Per-benchmark grouped bar chart
const benchColors = ['#06b6d4','#10b981','#f59e0b','#f43f5e','#8b5cf6','#ec4899','#0ea5e9','#84cc16','#fb923c','#a78bfa'];
const styledDatasets = benchDatasets.map((ds, i) => ({{
  ...ds,
  backgroundColor: benchColors[i % benchColors.length] + '99',
  borderColor: benchColors[i % benchColors.length],
  borderWidth: 1,
  borderRadius: 3,
}}));

new Chart(document.getElementById('benchChart'), {{
  type: 'bar',
  data: {{ labels: benchmarks, datasets: styledDatasets }},
  options: {{
    scales: {{
      y: {{ max: 100, ticks: {{ color: '#5a6a88', callback: v => v + '%' }}, grid: {{ color: 'rgba(255,255,255,0.04)' }}, border: {{ display: false }} }},
      x: {{ ticks: {{ color: '#8898b8', maxRotation: 40 }}, grid: {{ display: false }}, border: {{ display: false }} }}
    }},
    plugins: {{
      legend: {{ labels: {{ color: '#8898b8', boxWidth: 8, boxHeight: 8, usePointStyle: true, pointStyle: 'rect' }} }}
    }},
    responsive: true,
  }}
}});

// Matrix table
const headerEl = document.getElementById('matrix-header');
headerEl.innerHTML = '<th>Benchmark</th>' + models.map(m => `<th>${{m}}</th>`).join('');

const bodyEl = document.getElementById('matrix-body');
benchmarks.forEach(bench => {{
  let row = `<td class="bench-name">${{bench}}</td>`;
  models.forEach(m => {{
    const cell = matrix[m]?.[bench];
    if (cell) {{
      const pct = (cell.pass_at_k * 100).toFixed(1);
      const h = heatStyle(cell.pass_at_k);
      row += `<td>
        <span class="heat-pill" style="background:${{h.bg}};color:${{h.color}};border:1px solid ${{h.border}}">${{pct}}%</span>
        <span class="cell-count">${{cell.passed}}/${{cell.total}}</span>
      </td>`;
    }} else {{
      row += '<td><span class="heat-na">—</span></td>';
    }}
  }});
  bodyEl.innerHTML += `<tr>${{row}}</tr>`;
}});

// Fixture accordion
const detailsEl = document.getElementById('fixture-details');
models.forEach((m, mi) => {{
  const s = modelSummaries[m];
  const pct = (s.pass_at_k * 100).toFixed(1);
  const h = heatStyle(s.pass_at_k);

  let benchHTML = '';
  benchmarks.forEach(bench => {{
    const fl = simData[m]?.[bench] || [];
    if (!fl.length) return;
    benchHTML += `<div>
      <div class="fx-bench-header">${{bench}}</div>`;
    fl.forEach(f => {{
      const cls = f.passed ? 'pass' : 'fail';
      benchHTML += `<div class="fx-row">
        <div class="fx-id">${{f.id}}</div>
        <div class="fx-sim">${{f.sim}}%</div>
        <div class="result-pill ${{cls}}">${{f.passed ? 'PASS' : 'FAIL'}}</div>
      </div>`;
    }});
    benchHTML += '</div>';
  }});

  detailsEl.innerHTML += `
    <details class="fx-model">
      <summary class="fx-summary">
        <span class="fx-model-name">${{m}}</span>
        <div class="fx-right">
          <span class="heat-pill" style="background:${{h.bg}};color:${{h.color}};border:1px solid ${{h.border}}">${{pct}}%</span>
          <div class="fx-chevron">+</div>
        </div>
      </summary>
      <div class="fx-body">${{benchHTML}}</div>
    </details>`;
}});

// Run history
const runsBody = document.getElementById('runs-body');
runsMeta.forEach(r => {{
  const ts = r.timestamp ? new Date(r.timestamp).toLocaleString() : '—';
  const sha = r.git_sha ? r.git_sha.slice(0, 8) : '—';
  runsBody.innerHTML += `<tr>
    <td>${{ts}}</td>
    <td>${{r.model}}</td>
    <td>${{r.profile || '—'}}</td>
    <td class="sha-text">${{sha}}</td>
  </tr>`;
}});
</script>

</body>
</html>"""


def render_html_from_envelope(envelope: dict, title: str = "GitBench Report") -> str:
    """Render a single run envelope as an HTML report.

    Args:
        envelope: Run envelope dict with keys: version, model, profile, results, timestamp.
        title: HTML page title.

    Returns:
        Complete HTML string, or empty string on failure.
    """
    try:
        aggregated = aggregate_runs([envelope])
        return render_html(aggregated, title)
    except Exception as exc:
        logger.error("HTML generation failed: %s", exc)
        return ""
