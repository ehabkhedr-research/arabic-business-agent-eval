from typing import Dict, List
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from ar_biz_agent_eval.core.models import EvaluationResult


class TerminalReporter:
    """Renders rich, color-coded terminal reports for benchmark results."""

    def __init__(self, console: Console = None):
        self.console = console or Console()

    def print_summary(self, results: List[EvaluationResult], agent_name: str, model_name: str) -> None:
        if not results:
            self.console.print("[yellow]No evaluation results to report.[/yellow]")
            return

        total_scenarios = len(results)
        passed_scenarios = sum(1 for r in results if r.passed)
        overall_caas = sum(r.overall_score for r in results) / total_scenarios if total_scenarios > 0 else 0.0
        pass_rate = (passed_scenarios / total_scenarios) * 100 if total_scenarios > 0 else 0.0

        # Title Panel
        title_text = Text()
        title_text.append("📊 Arabic Business AI Agent Benchmark\n", style="bold cyan")
        title_text.append(f"Agent: [bold white]{agent_name}[/bold white] | Model: [cyan]{model_name}[/cyan]\n")
        title_text.append(f"Composite Score (CAAS): [bold green]{overall_caas:.3f}[/bold green] | Pass Rate: [bold]{pass_rate:.1f}%[/bold] ({passed_scenarios}/{total_scenarios})")

        self.console.print(Panel(title_text, expand=False, border_style="cyan"))

        # Metric Averages Table
        metric_sums: Dict[str, float] = {}
        metric_counts: Dict[str, int] = {}
        metric_weights: Dict[str, float] = {}

        for r in results:
            for m in r.metric_scores:
                metric_sums[m.name] = metric_sums.get(m.name, 0.0) + m.score
                metric_counts[m.name] = metric_counts.get(m.name, 0) + 1
                metric_weights[m.name] = m.weight

        metrics_table = Table(title="Key Benchmark Metric Dimensions", header_style="bold magenta", expand=False)
        metrics_table.add_column("Dimension", style="bold")
        metrics_table.add_column("Weight", justify="right")
        metrics_table.add_column("Average Score", justify="right")
        metrics_table.add_column("Benchmark Target", justify="right")
        metrics_table.add_column("Status", justify="center")

        target_map = {"GSCR": 0.80, "AVR": 0.85, "PEA": 0.80, "CES": 0.70, "TECI": 0.75}

        for m_name in ["GSCR", "AVR", "PEA", "CES", "TECI"]:
            if m_name in metric_sums:
                avg = metric_sums[m_name] / metric_counts[m_name]
                weight = metric_weights.get(m_name, 0.0)
                tgt = target_map.get(m_name, 0.70)
                status = "[green]PASS[/green]" if avg >= tgt else "[red]FAIL[/red]"
                score_style = "green" if avg >= tgt else "red"
                metrics_table.add_row(
                    m_name,
                    f"{weight:.2f}",
                    f"[{score_style}]{avg:.3f}[/{score_style}]",
                    f"{tgt:.2f}",
                    status,
                )

        self.console.print(metrics_table)

        # Dialect Breakdown Table
        dialect_table = Table(title="Performance Breakdown by Arabic Dialect", header_style="bold blue")
        dialect_table.add_column("Dialect", style="bold")
        dialect_table.add_column("Scenarios", justify="right")
        dialect_table.add_column("Passed", justify="right")
        dialect_table.add_column("Pass Rate", justify="right")
        dialect_table.add_column("Mean CAAS", justify="right")

        dialect_groups: Dict[str, List[EvaluationResult]] = {}
        for r in results:
            d_val = r.dialect.value if hasattr(r.dialect, "value") else str(r.dialect)
            dialect_groups.setdefault(d_val, []).append(r)

        for d_name, d_results in sorted(dialect_groups.items()):
            d_total = len(d_results)
            d_passed = sum(1 for x in d_results if x.passed)
            d_rate = (d_passed / d_total) * 100
            d_mean = sum(x.overall_score for x in d_results) / d_total
            color = "green" if d_rate >= 80 else "yellow" if d_rate >= 50 else "red"
            dialect_table.add_row(
                d_name,
                str(d_total),
                str(d_passed),
                f"[{color}]{d_rate:.1f}%[/{color}]",
                f"{d_mean:.3f}",
            )

        self.console.print(dialect_table)

        # Domain Breakdown Table
        domain_table = Table(title="Performance Breakdown by Business Domain", header_style="bold green")
        domain_table.add_column("Business Domain", style="bold")
        domain_table.add_column("Scenarios", justify="right")
        domain_table.add_column("Passed", justify="right")
        domain_table.add_column("Pass Rate", justify="right")
        domain_table.add_column("Mean CAAS", justify="right")

        domain_groups: Dict[str, List[EvaluationResult]] = {}
        for r in results:
            dom_val = r.domain.value if hasattr(r.domain, "value") else str(r.domain)
            domain_groups.setdefault(dom_val, []).append(r)

        for dom_name, dom_results in sorted(domain_groups.items()):
            dom_total = len(dom_results)
            dom_passed = sum(1 for x in dom_results if x.passed)
            dom_rate = (dom_passed / dom_total) * 100
            dom_mean = sum(x.overall_score for x in dom_results) / dom_total
            color = "green" if dom_rate >= 80 else "yellow" if dom_rate >= 50 else "red"
            domain_table.add_row(
                dom_name,
                str(dom_total),
                str(dom_passed),
                f"[{color}]{dom_rate:.1f}%[/{color}]",
                f"{dom_mean:.3f}",
            )

        self.console.print(domain_table)

        # Scenarios Status
        scen_table = Table(title="Scenario Execution Manifest", header_style="bold")
        scen_table.add_column("Scenario ID", style="bold")
        scen_table.add_column("Dialect")
        scen_table.add_column("Domain")
        scen_table.add_column("CAAS", justify="right")
        scen_table.add_column("Status", justify="center")

        for r in results:
            d_val = r.dialect.value if hasattr(r.dialect, "value") else str(r.dialect)
            dom_val = r.domain.value if hasattr(r.domain, "value") else str(r.domain)
            status_text = "[green]✓ PASS[/green]" if r.passed else "[red]✗ FAIL[/red]"
            score_color = "green" if r.overall_score >= 0.70 else "red"
            scen_table.add_row(
                r.scenario_id,
                d_val,
                dom_val,
                f"[{score_color}]{r.overall_score:.3f}[/{score_color}]",
                status_text,
            )

        self.console.print(scen_table)
