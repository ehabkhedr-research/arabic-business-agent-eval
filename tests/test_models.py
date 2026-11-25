import json
import pytest
from pydantic import ValidationError
from ar_biz_agent_eval.core.models import (
    DialectEnum,
    DomainEnum,
    Message,
    MetricScore,
    SessionState,
    ToolCall,
    ToolResult,
    EvaluationResult,
)
from ar_biz_agent_eval.core.scenario import (
    CulturalEtiquetteRubric,
    EvaluationCriteria,
    ExpectedToolCall,
    Scenario,
    StateAssertion,
    Turn,
)


def test_message_model_arabic_and_tools():
    """Verify Message model supports Arabic Unicode, diacritics, and tool calls."""
    msg = Message(
        role="assistant",
        content="حَيَّاكَ اللهُ يَا طَوِيلَ العُمْرِ، سَنَقُومُ بِخِدْمَتِكُمْ",
        tool_calls=[
            ToolCall(
                tool_name="generate_tax_invoice",
                arguments={"amount": 50000.0, "currency": "SAR"},
            )
        ],
    )
    assert msg.role == "assistant"
    assert "طَوِيلَ العُمْرِ" in msg.content
    assert len(msg.tool_calls) == 1

    # JSON roundtrip
    dumped = msg.model_dump_json()
    loaded = Message.model_validate_json(dumped)
    assert loaded.content == msg.content
    assert loaded.tool_calls[0].tool_name == "generate_tax_invoice"


def test_session_state_lifecycle():
    """Verify SessionState adds turns, records tool results, and calculates turn counts."""
    state = SessionState(scenario_id="ARAB-SCEN-001", agent_name="MockAgent", model_name="v1")
    assert state.turn_count == 0
    assert len(state.messages) == 0

    state.add_message(Message(role="user", content="نبي نسجل عميل جديد"))
    state.add_message(Message(role="assistant", content="أبشر، ما اسم الشركة؟"))
    assert state.turn_count == 1
    assert len(state.messages) == 2

    state.record_tool_call(
        ToolResult(
            tool_name="create_lead",
            arguments={"company_name": "شركة النجاح"},
            result={"lead_id": "LEAD-101"},
            latency_seconds=0.03,
        )
    )
    assert len(state.tool_calls) == 1
    assert state.tool_calls[0].tool_name == "create_lead"
    assert state.tool_calls[0].latency_seconds == 0.03

    # State serialization (2 user/assistant messages + 1 tool message recorded)
    json_data = state.model_dump()
    assert json_data["scenario_id"] == "ARAB-SCEN-001"
    assert len(json_data["conversation"]) == 3
    assert len(state.messages) == 3
    assert state.messages[-1].role == "tool"


def test_metric_score_and_evaluation_result():
    """Verify MetricScore and EvaluationResult structures."""
    m1 = MetricScore(name="AVR", score=1.0, weight=0.20, passed=True, details={"valid": 1})
    m2 = MetricScore(name="CES", score=0.85, weight=0.15, passed=True, details={"honorifics": True})

    res = EvaluationResult(
        scenario_id="ARAB-SCEN-001",
        scenario_title="فحص سجل المورد",
        agent_name="MockAgent",
        model_name="mock-v1",
        domain=DomainEnum.PROCUREMENT,
        dialect=DialectEnum.KHALEEJI,
        overall_score=0.92,
        passed=True,
        metrics=[m1, m2],
        turn_count=2,
    )
    assert res.overall_score == 0.92
    assert res.passed is True
    assert len(res.metrics) == 2

    # JSON export
    data = res.model_dump()
    assert data["domain"] == "procurement"
    assert data["dialect"] == "khaleeji"


def test_scenario_validation_strictness():
    """Verify Pydantic validation rejects invalid enums and missing required fields."""
    # Invalid domain
    with pytest.raises(ValidationError):
        Scenario(
            id="SCEN-FAIL",
            title="Invalid Domain",
            domain="non_existent_domain",  # Should fail
            dialect=DialectEnum.MSA,
            difficulty="easy",
            description="desc",
            turns=[],
            cultural_rubric=CulturalEtiquetteRubric(),
        )

    # Invalid dialect
    with pytest.raises(ValidationError):
        Scenario(
            id="SCEN-FAIL",
            title="Invalid Dialect",
            domain=DomainEnum.SALES,
            dialect="french_dialect",  # Should fail
            difficulty="easy",
            description="desc",
            turns=[],
            cultural_rubric=CulturalEtiquetteRubric(),
        )
