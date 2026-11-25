from datetime import datetime, timezone
from typing import Dict, List
from ar_biz_agent_eval.core.models import EvaluationResult


class MarkdownReporter:
    """Generates structured GitHub-Flavored Markdown benchmark evaluation reports."""

    def generate_report(
        self,
        results: List[EvaluationResult],
        agent_name: str,
        model_name: str,
    ) -> str:
        total_scenarios = len(results)
        passed_scenarios = sum(1 for r in results if r.passed)
        overall_caas = (
            sum(r.overall_score for r in results) / total_scenarios if total_scenarios > 0 else 0.0
        )
        pass_rate = (passed_scenarios / total_scenarios) * 100 if total_scenarios > 0 else 0.0
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        lines = [
            "# Arabic Business AI Agent Evaluation Report",
            "",
            f"> Generated on: `{timestamp}`  ",
            f"> Agent: **{agent_name}** | Model: `{model_name}`  ",
            f"> Composite Score (CAAS): **{overall_caas:.3f}** | Overall Pass Rate: **{pass_rate:.1f}%** ({passed_scenarios}/{total_scenarios})",
            "",
            "## 1. Executive Summary & Benchmark Dimensions",
            "",
            "| Dimension | Metric Name | Weight | Avg Score | Target | Benchmark Status |",
            "| :--- | :--- | :---: | :---: | :---: | :---: |",
        ]

        metric_sums: Dict[str, float] = {}
        metric_counts: Dict[str, int] = {}
        metric_weights: Dict[str, float] = {}
        for r in results:
            for m in r.metric_scores:
                metric_sums[m.name] = metric_sums.get(m.name, 0.0) + m.score
                metric_counts[m.name] = metric_counts.get(m.name, 0) + 1
                metric_weights[m.name] = m.weight

        dimension_labels = {
            "GSCR": "Goal & State Completion Rate",
            "AVR": "Action Validity Rate",
            "PEA": "Parameter Extraction Accuracy",
            "CES": "Cultural Etiquette Score",
            "TECI": "Turn & Cost Efficiency Index",
        }
        targets = {"GSCR": 0.80, "AVR": 0.85, "PEA": 0.80, "CES": 0.70, "TECI": 0.75}

        for m_name in ["GSCR", "AVR", "PEA", "CES", "TECI"]:
            if m_name in metric_sums:
                avg = metric_sums[m_name] / metric_counts[m_name]
                w = metric_weights.get(m_name, 0.0)
                tgt = targets.get(m_name, 0.70)
                status = "✅ PASS" if avg >= tgt else "❌ FAIL"
                label = dimension_labels.get(m_name, m_name)
                lines.append(f"| {label} | `{m_name}` | {w:.2f} | **{avg:.3f}** | {tgt:.2f} | {status} |")

        lines.extend([
            "",
            "## 2. Arabic Dialectal Performance Matrix",
            "",
            "| Dialect | Scenarios | Passed | Pass Rate | Mean CAAS |",
            "| :--- | :---: | :---: | :---: | :---: |",
        ])

        dialect_groups: Dict[str, List[EvaluationResult]] = {}
        for r in results:
            d_val = r.dialect.value if hasattr(r.dialect, "value") else str(r.dialect)
            dialect_groups.setdefault(d_val, []).append(r)

        for d_name, d_res in sorted(dialect_groups.items()):
            tot = len(d_res)
            pas = sum(1 for x in d_res if x.passed)
            rate = (pas / tot) * 100
            mean_sc = sum(x.overall_score for x in d_res) / tot
            lines.append(f"| **{d_name}** | {tot} | {pas} | {rate:.1f}% | {mean_sc:.3f} |")

        lines.extend([
            "",
            "## 3. Business Domain Breakdown",
            "",
            "| Domain | Scenarios | Passed | Pass Rate | Mean CAAS |",
            "| :--- | :---: | :---: | :---: | :---: |",
        ])

        domain_groups: Dict[str, List[EvaluationResult]] = {}
        for r in results:
            dom_val = r.domain.value if hasattr(r.domain, "value") else str(r.domain)
            domain_groups.setdefault(dom_val, []).append(r)

        for dom_name, dom_res in sorted(domain_groups.items()):
            tot = len(dom_res)
            pas = sum(1 for x in dom_res if x.passed)
            rate = (pas / tot) * 100
            mean_sc = sum(x.overall_score for x in dom_res) / tot
            lines.append(f"| **{dom_name}** | {tot} | {pas} | {rate:.1f}% | {mean_sc:.3f} |")

        lines.extend([
            "",
            "## 4. Detailed Scenario Execution Log",
            "",
            "| Scenario ID | Dialect | Domain | GSCR | AVR | PEA | CES | TECI | CAAS | Result |",
            "| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
        ])

        for r in results:
            d_val = r.dialect.value if hasattr(r.dialect, "value") else str(r.dialect)
            dom_val = r.domain.value if hasattr(r.domain, "value") else str(r.domain)
            m_map = {m.name: m.score for m in r.metric_scores}
            res_icon = "✅ PASS" if r.passed else "❌ FAIL"
            lines.append(
                f"| `{r.scenario_id}` | {d_val} | {dom_val} | "
                f"{m_map.get('GSCR', 0.0):.2f} | {m_map.get('AVR', 0.0):.2f} | "
                f"{m_map.get('PEA', 0.0):.2f} | {m_map.get('CES', 0.0):.2f} | "
                f"{m_map.get('TECI', 0.0):.2f} | **{r.overall_score:.3f}** | {res_icon} |"
            )

        lines.append("")
        return "\n".join(lines)
