import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from ar_biz_agent_eval.core.models import EvaluationResult


class JsonAndHtmlExporter:
    """Exports benchmark results to structured JSON and self-contained interactive HTML dashboards."""

    def export_json(
        self,
        results: List[EvaluationResult],
        agent_name: str,
        model_name: str,
        output_path: str,
    ) -> None:
        total_scenarios = len(results)
        passed_scenarios = sum(1 for r in results if r.passed)
        overall_caas = (
            sum(r.overall_score for r in results) / total_scenarios if total_scenarios > 0 else 0.0
        )

        data = {
            "metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "agent_name": agent_name,
                "model_name": model_name,
                "total_scenarios": total_scenarios,
                "passed_scenarios": passed_scenarios,
                "pass_rate_percent": round((passed_scenarios / total_scenarios) * 100, 2) if total_scenarios > 0 else 0.0,
                "overall_caas": round(overall_caas, 4),
            },
            "results": [r.model_dump() for r in results],
        }

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def export_html(
        self,
        results: List[EvaluationResult],
        agent_name: str,
        model_name: str,
        output_path: str,
    ) -> None:
        total_scenarios = len(results)
        passed_scenarios = sum(1 for r in results if r.passed)
        overall_caas = (
            sum(r.overall_score for r in results) / total_scenarios if total_scenarios > 0 else 0.0
        )
        pass_rate = (passed_scenarios / total_scenarios) * 100 if total_scenarios > 0 else 0.0
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        rows = []
        for r in results:
            d_val = r.dialect.value if hasattr(r.dialect, "value") else str(r.dialect)
            dom_val = r.domain.value if hasattr(r.domain, "value") else str(r.domain)
            m_map = {m.name: m.score for m in r.metric_scores}
            badge_class = "badge-pass" if r.passed else "badge-fail"
            badge_text = "PASS" if r.passed else "FAIL"
            rows.append(f"""
            <tr>
              <td><code>{r.scenario_id}</code></td>
              <td><span class="tag">{d_val}</span></td>
              <td><span class="tag tag-domain">{dom_val}</span></td>
              <td>{m_map.get('GSCR', 0.0):.2f}</td>
              <td>{m_map.get('AVR', 0.0):.2f}</td>
              <td>{m_map.get('PEA', 0.0):.2f}</td>
              <td>{m_map.get('CES', 0.0):.2f}</td>
              <td>{m_map.get('TECI', 0.0):.2f}</td>
              <td><strong>{r.overall_score:.3f}</strong></td>
              <td><span class="badge {badge_class}">{badge_text}</span></td>
            </tr>
            """)

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Arabic Business AI Agent Benchmark - {agent_name}</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      margin: 0; padding: 24px; background: #0d1117; color: #c9d1d9;
    }}
    .container {{ max-width: 1200px; margin: 0 auto; }}
    h1, h2, h3 {{ color: #58a6ff; }}
    .header-card {{
      background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; margin-bottom: 24px;
    }}
    .stat-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-top: 16px; }}
    .stat-box {{ background: #21262d; border-radius: 6px; padding: 12px 16px; border-left: 4px solid #58a6ff; }}
    .stat-val {{ font-size: 24px; font-weight: bold; color: #f0f6fc; }}
    .stat-lbl {{ font-size: 12px; color: #8b949e; text-transform: uppercase; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 16px; background: #161b22; border-radius: 8px; overflow: hidden; }}
    th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #30363d; }}
    th {{ background: #21262d; color: #f0f6fc; font-weight: 600; font-size: 13px; }}
    tr:hover {{ background: #1c2128; }}
    .badge {{ display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }}
    .badge-pass {{ background: rgba(46, 160, 67, 0.2); color: #3fb950; border: 1px solid #3fb950; }}
    .badge-fail {{ background: rgba(248, 81, 73, 0.2); color: #f85149; border: 1px solid #f85149; }}
    .tag {{ background: #30363d; padding: 2px 6px; border-radius: 4px; font-size: 11px; color: #e6edf3; }}
    .tag-domain {{ background: #1f6feb22; color: #58a6ff; border: 1px solid #1f6feb66; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header-card">
      <h1>Arabic Business AI Agent Benchmark Report</h1>
      <p>Agent: <strong>{agent_name}</strong> | Model: <code>{model_name}</code> | Generated: {timestamp}</p>
      <div class="stat-grid">
        <div class="stat-box">
          <div class="stat-val">{overall_caas:.3f}</div>
          <div class="stat-lbl">Composite Score (CAAS)</div>
        </div>
        <div class="stat-box">
          <div class="stat-val">{pass_rate:.1f}%</div>
          <div class="stat-lbl">Pass Rate</div>
        </div>
        <div class="stat-box">
          <div class="stat-val">{passed_scenarios} / {total_scenarios}</div>
          <div class="stat-lbl">Scenarios Passed</div>
        </div>
      </div>
    </div>

    <h2>Scenario Execution Results</h2>
    <table>
      <thead>
        <tr>
          <th>Scenario ID</th>
          <th>Dialect</th>
          <th>Domain</th>
          <th>GSCR</th>
          <th>AVR</th>
          <th>PEA</th>
          <th>CES</th>
          <th>TECI</th>
          <th>CAAS</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {"".join(rows)}
      </tbody>
    </table>
  </div>
</body>
</html>
"""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
