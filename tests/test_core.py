import pytest
from ar_biz_agent_eval.core.models import (
    DialectEnum,
    DomainEnum,
    Message,
    MetricScore,
    SessionState,
    ToolCall,
    ToolResult,
)
from ar_biz_agent_eval.core.scenario import (
    CulturalEtiquetteRubric,
    EvaluationCriteria,
    ExpectedOutcomes,
    ExpectedToolCall,
    Scenario,
    StateAssertion,
    Turn,
)
from ar_biz_agent_eval.core.registry import ScenarioRegistry, AgentRegistry, EvaluatorRegistry


def test_core_models_and_session_state():
    session = SessionState(
        scenario_id="ARAB-SCEN-TEST",
        agent_name="Test-Agent",
        model_name="mock-v1",
    )
    assert session.scenario_id == "ARAB-SCEN-TEST"
    assert session.turn_count == 0

    session.add_message(Message(role="user", content="مرحبا"))
    session.add_message(Message(role="assistant", content="أهلاً بك يا فندم"))
    assert session.turn_count == 1
    assert len(session.messages) == 2

    # Record tool call
    tr = ToolResult(
        tool_name="verify_vendor_cr",
        arguments={"cr_number": "CR-12345"},
        result={"status": "ACTIVE"},
        latency_seconds=0.05,
    )
    session.record_tool_call(tr)
    assert len(session.tool_calls) == 1
    assert session.tool_calls[0].tool_name == "verify_vendor_cr"


def test_scenario_creation_and_validation():
    scen = Scenario(
        id="ARAB-SCEN-999",
        title="اختبار تجريبي للتوريد",
        domain=DomainEnum.PROCUREMENT,
        dialect=DialectEnum.KHALEEJI,
        difficulty="standard",
        description="سيناريو تجريبي للاختبارات الآلية",
        context={"business_context": "فحص سجل الموردين بالرياض"},
        turns=[
            Turn(
                user_message="طال عمرك نبي نتأكد من المورد ونصدر أمر الشراء",
                expected_tool_calls=[
                    ExpectedToolCall(
                        tool_name="verify_vendor_cr",
                        arguments={"cr_number": "CR-1010"},
                    )
                ],
            )
        ],
        cultural_rubric=CulturalEtiquetteRubric(
            required_honorifics=["طال عمرك"],
            required_greetings=["حياك الله"],
            forbidden_phrases=["مشكلتكم"],
            face_saving_language_expected=True,
        ),
        state_assertions=[
            StateAssertion(
                entity="purchase_order",
                target_id="*",
                field="status",
                expected_value="ISSUED",
            )
        ],
        evaluation_criteria=EvaluationCriteria(
            golden_turn_count=1,
            max_allowed_turns=3,
        ),
    )
    assert scen.id == "ARAB-SCEN-999"
    assert scen.dialect == DialectEnum.KHALEEJI
    assert scen.domain == DomainEnum.PROCUREMENT
    assert len(scen.turns) == 1


def test_registries():
    scen_reg = ScenarioRegistry()
    assert scen_reg.count() == 0

    scen = Scenario(
        id="TEST-001",
        title="Test Scenario",
        domain=DomainEnum.SALES,
        dialect=DialectEnum.MASRI,
        difficulty="standard",
        description="Demo",
        context={"business_context": "Testing"},
        turns=[],
        cultural_rubric=CulturalEtiquetteRubric(),
        evaluation_criteria=EvaluationCriteria(),
    )
    scen_reg.register(scen)
    assert scen_reg.count() == 1
    assert scen_reg.get("TEST-001") is not None
    assert scen_reg.get("NON_EXISTENT") is None

    # Filter
    masri_scens = scen_reg.filter(dialect=DialectEnum.MASRI)
    assert len(masri_scens) == 1
    khaleeji_scens = scen_reg.filter(dialect=DialectEnum.KHALEEJI)
    assert len(khaleeji_scens) == 0
