import json
from pathlib import Path
import pytest
from typer.testing import CliRunner
from ar_biz_agent_eval.agents.mock_agent import MockAgent
from ar_biz_agent_eval.agents.runner import EvaluationRunner
from ar_biz_agent_eval.cli.main import app
from ar_biz_agent_eval.core.registry import scenario_registry
from ar_biz_agent_eval.environments.business_suite import BusinessEnvironment
from ar_biz_agent_eval.evaluators.composite import CompositeEvaluator
from ar_biz_agent_eval.scenarios.loader import ScenarioLoader

runner = CliRunner()


@pytest.fixture(autouse=True)
def load_all_scenarios():
    ScenarioLoader().load_builtin_scenarios()


def test_runner_end_to_end_with_mock_agent():
    scen = scenario_registry.get("ARAB-SCEN-001")
    assert scen is not None

    agent = MockAgent(mode="golden")
    env = BusinessEnvironment()
    eval_runner = EvaluationRunner()

    session = eval_runner.run_scenario(scen, agent, env)
    assert session.scenario_id == scen.id
    assert session.turn_count >= 1
    assert len(session.tool_calls) >= 1

    composite = CompositeEvaluator()
    res = composite.evaluate(scen, session, env)
    assert res.overall_score >= 0.70
    assert res.passed is True


def test_cli_scenarios_list():
    result = runner.invoke(app, ["scenarios", "list"])
    assert result.exit_code == 0
    assert "ARAB-SCEN-001" in result.stdout
    assert "Total scenarios" in result.stdout


def test_cli_inspect():
    result = runner.invoke(app, ["inspect", "ARAB-SCEN-001"])
    assert result.exit_code == 0
    assert "ARAB-SCEN-001" in result.stdout
    assert "Cultural Etiquette Rubric" in result.stdout


def test_cli_run_single_scenario(tmp_path):
    report_dir = tmp_path / "reports"
    result = runner.invoke(
        app,
        [
            "run",
            "--scenario",
            "ARAB-SCEN-001",
            "--agent",
            "mock",
            "--report-dir",
            str(report_dir),
        ],
    )
    assert result.exit_code == 0
    assert "Arabic Business AI Agent Benchmark" in result.stdout
    assert "PASS" in result.stdout

    # Verify generated files
    assert (report_dir / "benchmark_report.md").exists()
    assert (report_dir / "benchmark_results.json").exists()
    assert (report_dir / "benchmark_dashboard.html").exists()

    with open(report_dir / "benchmark_results.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["metadata"]["total_scenarios"] == 1
        assert data["metadata"]["passed_scenarios"] == 1
