import pytest
from ar_biz_agent_eval.agents.base import AgentResponse, BaseAgent
from ar_biz_agent_eval.agents.mock_agent import MockAgent
from ar_biz_agent_eval.agents.openai_agent import OpenAIAgent
from ar_biz_agent_eval.agents.anthropic_agent import AnthropicAgent
from ar_biz_agent_eval.core.models import Message, ToolCall
from ar_biz_agent_eval.environments.base import ToolDefinition, ToolParameter


def test_mock_agent_golden_mode():
    agent = MockAgent(mode="golden")
    tools = [
        ToolDefinition(
            name="verify_vendor_cr",
            description="Verify CR",
            parameters=[ToolParameter(name="cr_number", type="string", description="CR number")],
            handler=lambda cr_number: None,
        )
    ]
    messages = [Message(role="user", content="طال عمرك نبي نسجل عميل ونشيك السجل")]
    resp = agent.act(messages, tools)
    assert isinstance(resp, AgentResponse)
    assert len(resp.message) > 0
    # Culturally polite
    assert any(h in resp.message for h in ["طال عمرك", "طويل العمر", "سعادتكم", "أهلاً", "السلام عليكم"])


def test_mock_agent_blunt_refusal_mode():
    agent = MockAgent(mode="blunt_refusal")
    messages = [Message(role="user", content="نرجو حل المشكلة وتصعيد التذكرة")]
    resp = agent.act(messages, [])
    assert len(resp.tool_calls) == 0
    assert "هذه ليست مشكلتي" in resp.message


def test_mock_agent_hallucinated_tool_mode():
    agent = MockAgent(mode="hallucinated_tool")
    messages = [Message(role="user", content="عايزين حل")]
    resp = agent.act(messages, [])
    assert len(resp.tool_calls) == 1
    assert resp.tool_calls[0].tool_name == "unregistered_magic_resolver"


def test_tool_definition_schema_export():
    tool = ToolDefinition(
        name="test_tool",
        description="A test tool",
        parameters=[
            ToolParameter(name="param1", type="string", description="P1", required=True),
            ToolParameter(name="param2", type="number", description="P2", required=False),
        ],
        handler=lambda **kwargs: None,
    )
    openai_schema = tool.to_openai_schema()
    assert openai_schema["type"] == "function"
    assert openai_schema["function"]["name"] == "test_tool"
    assert "param1" in openai_schema["function"]["parameters"]["properties"]
    assert "param1" in openai_schema["function"]["parameters"]["required"]
    assert "param2" not in openai_schema["function"]["parameters"]["required"]

    anthropic_schema = tool.to_anthropic_schema()
    assert anthropic_schema["name"] == "test_tool"
    assert "param1" in anthropic_schema["input_schema"]["properties"]
