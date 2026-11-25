import pytest
from ar_biz_agent_eval.core.models import DialectEnum, DomainEnum
from ar_biz_agent_eval.core.registry import scenario_registry
from ar_biz_agent_eval.scenarios.loader import ScenarioLoader


def test_scenario_loader_loads_all_scenarios():
    loader = ScenarioLoader()
    count = loader.load_builtin_scenarios()
    assert count == 20
    assert scenario_registry.count() == 20

    # Check all 20 scenarios exist and validate properly
    for i in range(1, 21):
        expected_id = f"ARAB-SCEN-{i:03d}"
        scen = scenario_registry.get(expected_id)
        assert scen is not None, f"Scenario {expected_id} missing!"
        assert scen.cultural_rubric is not None
        assert len(scen.turns) > 0
        assert scen.domain is not None
        assert scen.dialect is not None
        assert scen.title
        assert scen.description
        assert scen.evaluation_criteria.golden_turn_count >= 1


def test_scenario_dialect_and_domain_distribution():
    loader = ScenarioLoader()
    loader.load_builtin_scenarios()

    scenarios = scenario_registry.list_all()
    dialects = {s.dialect for s in scenarios}
    domains = {s.domain for s in scenarios}

    # Verify all target dialects are represented
    assert DialectEnum.MSA in dialects
    assert DialectEnum.KHALEEJI in dialects
    assert DialectEnum.MASRI in dialects
    assert DialectEnum.SHAMI in dialects
    assert DialectEnum.CODE_SWITCHING in dialects

    # Verify all target business domains are represented
    assert DomainEnum.PROCUREMENT in domains
    assert DomainEnum.SALES in domains
    assert DomainEnum.BILLING in domains
    assert DomainEnum.SUPPORT in domains
