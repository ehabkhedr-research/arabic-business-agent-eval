import json
from pathlib import Path
import pytest
from typer.testing import CliRunner
from ar_biz_agent_eval.cli.main import app
from ar_biz_agent_eval.scenarios.loader import ScenarioLoader

runner = CliRunner()


@pytest.fixture(autouse=True)
def load_all_scenarios():
    ScenarioLoader().load_builtin_scenarios()


def test_cli_help():
    """Verify top-level CLI help text."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Arabic Business AI Agent Benchmark" in result.stdout
    assert "run" in result.stdout
    assert "scenarios" in result.stdout
    assert "inspect" in result.stdout
    assert "report" in result.stdout


def test_cli_scenarios_list_filters():
    """Verify listing scenarios with dialect and domain filters."""
    # List all
    res_all = runner.invoke(app, ["scenarios", "list"])
    assert res_all.exit_code == 0
    assert "Total scenarios: 20" in res_all.stdout

    # Filter by dialect
    res_khaleeji = runner.invoke(app, ["scenarios", "list", "--dialect", "khaleeji"])
    assert res_khaleeji.exit_code == 0
    assert "khaleeji" in res_khaleeji.stdout
    assert "Total scenarios" in res_khaleeji.stdout

    # Filter by domain
    res_billing = runner.invoke(app, ["scenarios", "list", "--domain", "billing"])
    assert res_billing.exit_code == 0
    assert "billing" in res_billing.stdout


def test_cli_inspect_and_show():
    """Verify inspect and scenarios show commands."""
    res_inspect = runner.invoke(app, ["inspect", "ARAB-SCEN-001"])
    assert res_inspect.exit_code == 0
    assert "ARAB-SCEN-001" in res_inspect.stdout
    assert "Cultural Etiquette Rubric" in res_inspect.stdout
    assert "Required Honorifics" in res_inspect.stdout

    res_show = runner.invoke(app, ["scenarios", "show", "ARAB-SCEN-001"])
    assert res_show.exit_code == 0
    assert "ARAB-SCEN-001" in res_show.stdout

    # Inspect invalid scenario
    res_invalid = runner.invoke(app, ["inspect", "INVALID-SCENARIO-ID"])
    assert res_invalid.exit_code != 0
    assert "not found" in res_invalid.stdout


def test_cli_run_filter_modes(tmp_path):
    """Verify CLI run with different agent modes and filters."""
    out_dir = tmp_path / "reports"

    # Golden Mock Agent run on single scenario
    res_golden = runner.invoke(
        app,
        [
            "run",
            "--scenario", "ARAB-SCEN-001",
            "--agent", "mock",
            "--report-dir", str(out_dir),
        ],
    )
    assert res_golden.exit_code == 0
    assert (out_dir / "benchmark_report.md").exists()
    assert (out_dir / "benchmark_results.json").exists()
    assert (out_dir / "benchmark_dashboard.html").exists()

    # Faulty Mock Agent run
    res_faulty = runner.invoke(
        app,
        [
            "run",
            "--scenario", "ARAB-SCEN-001",
            "--agent", "mock-faulty",
            "--report-dir", str(out_dir / "faulty"),
        ],
    )
    assert res_faulty.exit_code == 0

    # Blunt Refusal Mock Agent run
    res_blunt = runner.invoke(
        app,
        [
            "run",
            "--scenario", "ARAB-SCEN-001",
            "--agent", "mock-blunt",
            "--report-dir", str(out_dir / "blunt"),
        ],
    )
    assert res_blunt.exit_code == 0

    # Nonexistent scenario
    res_none = runner.invoke(app, ["run", "--scenario", "NONEXISTENT"])
    assert res_none.exit_code != 0


def test_cli_report_view(tmp_path):
    """Verify report view command for JSON and Markdown files."""
    out_dir = tmp_path / "rep_view"
    runner.invoke(
        app,
        [
            "run",
            "--scenario", "ARAB-SCEN-001",
            "--agent", "mock",
            "--report-dir", str(out_dir),
        ],
    )

    json_file = out_dir / "benchmark_results.json"
    md_file = out_dir / "benchmark_report.md"

    # View JSON report
    res_json = runner.invoke(app, ["report", "view", str(json_file)])
    assert res_json.exit_code == 0
    assert "Report Summary" in res_json.stdout

    # View Markdown report
    res_md = runner.invoke(app, ["report", "view", str(md_file)])
    assert res_md.exit_code == 0

    # View missing report
    res_missing = runner.invoke(app, ["report", "view", str(out_dir / "nonexistent.json")])
    assert res_missing.exit_code != 0
