import pytest
from ar_biz_agent_eval.core.models import Message, SessionState, ToolCall, ToolResult
from ar_biz_agent_eval.core.scenario import (
    CulturalEtiquetteRubric,
    EvaluationCriteria,
    ExpectedToolCall,
    Scenario,
    StateAssertion,
    Turn,
    DialectEnum,
    DomainEnum,
)
from ar_biz_agent_eval.environments.business_suite import BusinessEnvironment
from ar_biz_agent_eval.evaluators.cultural_safety_eval import ArabicCulturalSafetyEvaluator
from ar_biz_agent_eval.evaluators.efficiency_eval import EfficiencyEvaluator
from ar_biz_agent_eval.evaluators.goal_state_eval import BusinessGoalEvaluator
from ar_biz_agent_eval.evaluators.tool_call_eval import ToolCallEvaluator
from ar_biz_agent_eval.evaluators.composite import CompositeEvaluator


@pytest.fixture
def sample_scenario():
    return Scenario(
        id="ARAB-TEST-001",
        title="Test Billing Scenario",
        domain=DomainEnum.BILLING,
        dialect=DialectEnum.KHALEEJI,
        difficulty="standard",
        description="Billing test",
        context={"business_context": "VAT calculation"},
        turns=[
            Turn(
                user_message="طال عمرك نبي فاتورة ضريبية للمؤسسة 50000 ريال مع الرقم الضريبي 300000000000003",
                expected_tool_calls=[
                    ExpectedToolCall(
                        tool_name="generate_tax_invoice",
                        arguments={
                            "customer_name": "شركة الخليج",
                            "customer_vat_number": "300000000000003",
                            "currency": "SAR",
                        },
                    )
                ],
            )
        ],
        cultural_rubric=CulturalEtiquetteRubric(
            required_honorifics=["طال عمرك"],
            required_greetings=["حياك الله"],
            forbidden_phrases=["ادفع أولاً"],
            face_saving_language_expected=True,
        ),
        state_assertions=[
            StateAssertion(
                entity="tax_invoice",
                target_id="300000000000003",
                field="gross_amount",
                expected_value=57500.0,
                operator="==",
            )
        ],
        evaluation_criteria=EvaluationCriteria(golden_turn_count=1, max_allowed_turns=2),
    )


def test_evaluators_with_golden_execution(sample_scenario):
    env = BusinessEnvironment()
    # Execute actual invoice tool in environment
    inv_res = env.billing.generate_tax_invoice(
        customer_name="شركة الخليج",
        customer_vat_number="300000000000003",
        items=[{"name": "خدمات حوسبة", "quantity": 1, "unit_price": 50000.0}],
        currency="SAR",
    )

    session = SessionState(scenario_id=sample_scenario.id, agent_name="MockAgent")
    session.add_message(Message(role="user", content=sample_scenario.turns[0].user_message))
    session.add_message(
        Message(
            role="assistant",
            content="حياك الله طال عمرك وأبشر بالخير، تم إصدار الفاتورة الضريبية المعتمدة لسعادتكم بكل سرور.",
        )
    )
    session.record_tool_call(
        ToolResult(
            tool_name="generate_tax_invoice",
            arguments={
                "customer_name": "شركة الخليج",
                "customer_vat_number": "300000000000003",
                "currency": "SAR",
            },
            result=inv_res.data,
            latency_seconds=0.02,
        )
    )

    # 1. Goal State
    gscr_eval = BusinessGoalEvaluator()
    gscr_score = gscr_eval.evaluate(sample_scenario, session, env)
    assert gscr_score.score == 1.0
    assert gscr_score.passed is True

    # 2. Tool Calls
    tc_eval = ToolCallEvaluator()
    scores = tc_eval.evaluate(sample_scenario, session, env)
    avr = next(s for s in scores if s.name == "AVR")
    pea = next(s for s in scores if s.name == "PEA")
    assert avr.score == 1.0
    assert pea.score == 1.0

    # 3. Cultural Safety
    ces_eval = ArabicCulturalSafetyEvaluator()
    ces_score = ces_eval.evaluate(sample_scenario, session, env)
    assert ces_score.score >= 0.8
    assert ces_score.passed is True

    # 4. Efficiency
    teci_eval = EfficiencyEvaluator()
    teci_score = teci_eval.evaluate(sample_scenario, session, env)
    assert teci_score.score == 1.0

    # 5. Composite Evaluator
    composite = CompositeEvaluator()
    result = composite.evaluate(sample_scenario, session, env)
    assert result.overall_score >= 0.90
    assert result.passed is True


def test_evaluator_forbidden_phrase_failure(sample_scenario):
    env = BusinessEnvironment()
    session = SessionState(scenario_id=sample_scenario.id, agent_name="MockAgent")
    session.add_message(Message(role="user", content="نبي الفاتورة"))
    # Agent uses forbidden phrase "ادفع أولاً"
    session.add_message(Message(role="assistant", content="ادفع أولاً لكي نصدر لك الفاتورة"))

    ces_eval = ArabicCulturalSafetyEvaluator()
    ces_score = ces_eval.evaluate(sample_scenario, session, env)
    assert ces_score.score == 0.0
    assert ces_score.passed is False
    assert "Forbidden" in ces_score.details.get("violation", "")


def test_evaluator_missing_tool_call_pea_zero(sample_scenario):
    """Verify PEA is 0.0 when expected tool calls are completely omitted."""
    env = BusinessEnvironment()
    session = SessionState(scenario_id=sample_scenario.id, agent_name="MockAgent")
    session.add_message(Message(role="user", content=sample_scenario.turns[0].user_message))
    session.add_message(Message(role="assistant", content="أهلاً بك، تم استلام الطلب دون تنفيذ أي أدوات."))

    tc_eval = ToolCallEvaluator()
    scores = tc_eval.evaluate(sample_scenario, session, env)
    pea = next(s for s in scores if s.name == "PEA")
    avr = next(s for s in scores if s.name == "AVR")
    assert pea.score == 0.0
    assert pea.passed is False
    assert avr.score == 0.0


def test_evaluator_unregistered_tool_avr_penalty(sample_scenario):
    """Verify AVR is penalized when agent calls an unregistered/hallucinated tool."""
    env = BusinessEnvironment()
    session = SessionState(scenario_id=sample_scenario.id, agent_name="MockAgent")
    session.add_message(Message(role="user", content=sample_scenario.turns[0].user_message))
    session.add_message(Message(role="assistant", content="حياك الله، جاري المعالجة"))
    session.record_tool_call(
        ToolResult(
            tool_name="hallucinated_magic_action",
            arguments={"param": "value"},
            result={"status": "error"},
            error="Tool not found",
            latency_seconds=0.01,
        )
    )

    tc_eval = ToolCallEvaluator()
    scores = tc_eval.evaluate(sample_scenario, session, env)
    avr = next(s for s in scores if s.name == "AVR")
    assert avr.score == 0.0
    assert avr.passed is False


def test_evaluator_excessive_turns_efficiency_penalty(sample_scenario):
    """Verify EfficiencyEvaluator penalizes agents that take excessive turns."""
    env = BusinessEnvironment()
    session = SessionState(scenario_id=sample_scenario.id, agent_name="MockAgent")
    # Add 4 turns (scenario golden_turn_count=1, max_allowed_turns=2)
    for i in range(4):
        session.add_message(Message(role="user", content=f"رسالة {i}"))
        session.add_message(Message(role="assistant", content=f"رد {i}"))

    teci_eval = EfficiencyEvaluator()
    teci_score = teci_eval.evaluate(sample_scenario, session, env)
    assert teci_score.score < 1.0
    assert teci_score.details["actual_turns"] == 4
