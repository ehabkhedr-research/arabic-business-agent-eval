import os
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ar_biz_agent_eval.agents.base import BaseAgent
from ar_biz_agent_eval.agents.mock_agent import MockAgent
from ar_biz_agent_eval.agents.openai_agent import OpenAIAgent
from ar_biz_agent_eval.agents.gemini_agent import GeminiAgent
from ar_biz_agent_eval.agents.anthropic_agent import AnthropicAgent
from ar_biz_agent_eval.agents.http_a2a_agent import HttpA2AAgent
from ar_biz_agent_eval.agents.runner import EvaluationRunner
from ar_biz_agent_eval.core.models import DialectEnum, DomainEnum
from ar_biz_agent_eval.core.registry import scenario_registry
from ar_biz_agent_eval.environments.business_suite import BusinessEnvironment
from ar_biz_agent_eval.evaluators.composite import CompositeEvaluator
from ar_biz_agent_eval.reporting.terminal import TerminalReporter
from ar_biz_agent_eval.reporting.markdown import MarkdownReporter
from ar_biz_agent_eval.reporting.json_export import JsonAndHtmlExporter
from ar_biz_agent_eval.scenarios.loader import ScenarioLoader

app = typer.Typer(
    name="ar-eval",
    help="Arabic Business AI Agent Benchmark - Evaluation CLI for MENA Enterprise Scenarios",
    no_args_is_help=True,
)
scenarios_app = typer.Typer(help="Manage and list evaluation scenarios")
app.add_typer(scenarios_app, name="scenarios")
report_app = typer.Typer(help="View and inspect generated evaluation reports")
app.add_typer(report_app, name="report")

console = Console()


def _ensure_scenarios_loaded():
    if scenario_registry.count() == 0:
        loader = ScenarioLoader()
        loader.load_builtin_scenarios()


def _get_agent(agent_type: str, model_name: Optional[str] = None) -> BaseAgent:
    a_type = agent_type.lower()
    if a_type in ("mock", "mock-golden", "golden"):
        return MockAgent(name="Deterministic-Mock", mode="golden", model_name=model_name or "mock-golden-v1")
    elif a_type in ("mock-faulty", "faulty"):
        return MockAgent(name="Faulty-Mock", mode="faulty_params", model_name=model_name or "mock-faulty-v1")
    elif a_type in ("mock-blunt", "blunt"):
        return MockAgent(name="Blunt-Refusal-Mock", mode="blunt_refusal", model_name=model_name or "mock-blunt-v1")
    elif a_type in ("mock-hallucinated", "hallucinated"):
        return MockAgent(name="Hallucinating-Mock", mode="hallucinated_tool", model_name=model_name or "mock-hallucinated-v1")
    elif a_type in ("openai", "gpt"):
        return OpenAIAgent(name="OpenAI-Agent", model_name=model_name or "gpt-4o")
    elif a_type in ("gemini", "google"):
        return GeminiAgent(name="Gemini-Agent", model_name=model_name or "gemini-2.0-flash")
    elif a_type in ("anthropic", "claude"):
        return AnthropicAgent(name="Anthropic-Agent", model_name=model_name or "claude-3-5-sonnet-20241022")
    elif a_type in ("http", "a2a"):
        endpoint = os.getenv("A2A_ENDPOINT", "http://localhost:8000/agent/act")
        return HttpA2AAgent(name="HTTP-Agent", endpoint=endpoint)
    else:
        console.print(f"[yellow]Unknown agent '{agent_type}'. Defaulting to mock-golden.[/yellow]")
        return MockAgent(name="Deterministic-Mock", mode="golden", model_name=model_name or "mock-golden-v1")


@app.command(name="run")
def run_benchmark(
    scenario_id: Optional[str] = typer.Option(None, "--scenario", "-s", help="Specific scenario ID (e.g. ARAB-SCEN-001)"),
    dialect: Optional[str] = typer.Option(None, "--dialect", "-d", help="Filter by dialect: msa, khaleeji, masri, shami, code_switching"),
    domain: Optional[str] = typer.Option(None, "--domain", help="Filter by domain: procurement, sales, billing, support"),
    agent_type: str = typer.Option("mock", "--agent", "-a", help="Agent adapter: mock, mock-faulty, mock-blunt, openai, gemini, anthropic, http"),
    model_name: Optional[str] = typer.Option(None, "--model", "-m", help="Model name identifier"),
    output_dir: str = typer.Option("./reports", "--report-dir", help="Directory to export Markdown, JSON, and HTML reports"),
):
    """Execute the Arabic business benchmark against specified scenarios and agents."""
    _ensure_scenarios_loaded()

    # Filter scenarios
    scenarios = scenario_registry.list_all()

    if scenario_id:
        scenarios = [s for s in scenarios if s.id.lower() == scenario_id.lower()]
    if dialect:
        scenarios = [s for s in scenarios if s.dialect.value.lower() == dialect.lower()]
    if domain:
        scenarios = [s for s in scenarios if s.domain.value.lower() == domain.lower()]

    if not scenarios:
        console.print(f"[red]No scenarios found matching filters (id={scenario_id}, dialect={dialect}, domain={domain}).[/red]")
        raise typer.Exit(code=1)

    agent = _get_agent(agent_type, model_name)
    runner = EvaluationRunner()
    composite_eval = CompositeEvaluator()

    results = []
    with console.status(f"[bold green]Running benchmark across {len(scenarios)} scenarios with agent '{agent.name}'..."):
        for scen in scenarios:
            env = BusinessEnvironment()
            session = runner.run_scenario(scen, agent, env)
            eval_res = composite_eval.evaluate(scen, session, env)
            results.append(eval_res)

    # 1. Terminal Report
    reporter = TerminalReporter(console)
    reporter.print_summary(results, agent.name, agent.model_name)

    # 2. Export Artifacts
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    md_path = out_path / "benchmark_report.md"
    json_path = out_path / "benchmark_results.json"
    html_path = out_path / "benchmark_dashboard.html"

    md_content = MarkdownReporter().generate_report(results, agent.name, agent.model_name)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    exporter = JsonAndHtmlExporter()
    exporter.export_json(results, agent.name, agent.model_name, str(json_path))
    exporter.export_html(results, agent.name, agent.model_name, str(html_path))

    console.print(f"\n[green]✓ Reports exported to:[/green]")
    console.print(f"  • Markdown: [cyan]{md_path}[/cyan]")
    console.print(f"  • JSON:     [cyan]{json_path}[/cyan]")
    console.print(f"  • HTML:     [cyan]{html_path}[/cyan]\n")


@scenarios_app.command(name="list")
def list_scenarios(
    dialect: Optional[str] = typer.Option(None, "--dialect", "-d", help="Filter by dialect"),
    domain: Optional[str] = typer.Option(None, "--domain", help="Filter by domain"),
):
    """List all available curated benchmark scenarios."""
    _ensure_scenarios_loaded()
    scenarios = scenario_registry.list_all()

    if dialect:
        scenarios = [s for s in scenarios if s.dialect.value.lower() == dialect.lower()]
    if domain:
        scenarios = [s for s in scenarios if s.domain.value.lower() == domain.lower()]

    table = Table(title="Curated Arabic Business Benchmark Scenarios", header_style="bold cyan")
    table.add_column("Scenario ID", style="bold", no_wrap=True)
    table.add_column("Title")
    table.add_column("Dialect", style="magenta")
    table.add_column("Domain", style="blue")
    table.add_column("Turns", justify="right")
    table.add_column("Difficulty", justify="center")

    for s in scenarios:
        diff_color = "green" if s.difficulty == "standard" else "yellow" if s.difficulty == "hard" else "red"
        title_str = s.title_display if hasattr(s, "title_display") and isinstance(s.title, dict) else str(s.title)
        table.add_row(
            s.id,
            title_str,
            s.dialect.value,
            s.domain.value,
            str(len(s.turns)),
            f"[{diff_color}]{s.difficulty}[/{diff_color}]",
        )

    console.print(table)
    console.print(f"Total scenarios: [bold]{len(scenarios)}[/bold]\n")


@app.command(name="inspect")
def inspect_scenario(scenario_id: str = typer.Argument(..., help="Scenario ID to inspect (e.g. ARAB-SCEN-001)")):
    """Inspect detailed information, rubric, and conversation turns of a scenario."""
    _ensure_scenarios_loaded()
    scen = scenario_registry.get(scenario_id)
    if not scen:
        console.print(f"[red]Scenario '{scenario_id}' not found.[/red]")
        raise typer.Exit(code=1)

    title_val = scen.title_display if hasattr(scen, "title_display") and isinstance(scen.title, dict) else str(scen.title)
    desc_val = scen.description_display if hasattr(scen, "description_display") and isinstance(scen.description, dict) else str(scen.description)
    ctx_val = getattr(scen.context, "business_context", "") or (scen.context.get("business_context", "") if isinstance(scen.context, dict) else str(scen.context))

    panel_text = f"[bold cyan]ID:[/bold cyan] {scen.id}\n"
    panel_text += f"[bold cyan]Title:[/bold cyan] {title_val}\n"
    panel_text += f"[bold cyan]Dialect:[/bold cyan] {scen.dialect.value} | [bold cyan]Domain:[/bold cyan] {scen.domain.value} | [bold cyan]Difficulty:[/bold cyan] {scen.difficulty}\n"
    panel_text += f"[bold cyan]Description:[/bold cyan] {desc_val}\n"
    panel_text += f"[bold cyan]Context:[/bold cyan] {ctx_val}\n"

    console.print(Panel(panel_text, title=f"Scenario Specification: {scen.id}", border_style="cyan"))

    console.print("\n[bold magenta]Conversation Turns & Expected Outcomes:[/bold magenta]")
    for i, t in enumerate(scen.turns, 1):
        console.print(f"\n  [bold yellow]Turn {i}:[/bold yellow]")
        console.print(f"    [bold]User:[/bold] {t.user_message}")
        if t.expected_tool_calls:
            console.print("    [bold]Expected Tools:[/bold]")
            for etc in t.expected_tool_calls:
                console.print(f"      • [green]{etc.tool_name}[/green] args={etc.arguments}")

    console.print("\n[bold magenta]Cultural Etiquette Rubric:[/bold magenta]")
    console.print(f"  • Required Honorifics: {scen.cultural_rubric.required_honorifics}")
    console.print(f"  • Required Greetings:  {scen.cultural_rubric.required_greetings}")
    console.print(f"  • Forbidden Phrases:   {scen.cultural_rubric.forbidden_phrases}")
    console.print(f"  • Face Saving Expected:{scen.cultural_rubric.face_saving_language_expected}")

    if scen.state_assertions:
        console.print("\n[bold magenta]State Assertions:[/bold magenta]")
        for sa in scen.state_assertions:
            console.print(f"  • Entity={sa.entity} Target={sa.target_id} Field={sa.field} {sa.operator} {sa.expected_value}")
    console.print("")


@scenarios_app.command(name="show")
def show_scenario(scenario_id: str = typer.Argument(..., help="Scenario ID to inspect (e.g. ARAB-SCEN-001)")):
    """Show detailed specification of a specific scenario (alias for inspect)."""
    inspect_scenario(scenario_id)


@report_app.command(name="view")
def view_report(report_path: str = typer.Argument(..., help="Path to markdown or json report")):
    """View evaluation report summary directly in the terminal."""
    p = Path(report_path)
    if not p.exists():
        console.print(f"[red]Report file not found: {report_path}[/red]")
        raise typer.Exit(code=1)
    
    with open(p, "r", encoding="utf-8") as f:
        content = f.read()
    
    if p.suffix.lower() == ".json":
        import json
        data = json.loads(content)
        meta = data.get("metadata", {})
        console.print(Panel(
            f"[bold cyan]Agent:[/bold cyan] {meta.get('agent_name')} ({meta.get('model_name')})\n"
            f"[bold cyan]Total Scenarios:[/bold cyan] {meta.get('total_scenarios')}\n"
            f"[bold cyan]Passed Scenarios:[/bold cyan] {meta.get('passed_scenarios')}\n"
            f"[bold cyan]Average Score:[/bold cyan] {meta.get('average_score', 0):.2f}\n"
            f"[bold cyan]Timestamp:[/bold cyan] {meta.get('timestamp')}",
            title=f"Report Summary: {p.name}",
            border_style="green",
        ))
    else:
        from rich.markdown import Markdown
        console.print(Markdown(content))


def main():
    app()


if __name__ == "__main__":
    main()
