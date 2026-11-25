import json
import os
from typing import Any, Dict, List, Optional
from ar_biz_agent_eval.agents.base import AgentResponse, BaseAgent
from ar_biz_agent_eval.core.models import Message, ToolCall
from ar_biz_agent_eval.environments.base import ToolDefinition


class AnthropicAgent(BaseAgent):
    """Adapter for Anthropic Claude models (e.g. claude-3-5-sonnet-20241022)."""

    def __init__(
        self,
        name: str = "Anthropic-Agent",
        model_name: str = "claude-3-5-sonnet-20241022",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.0,
        system_prompt: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(name=name, model_name=model_name, **kwargs)
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.base_url = base_url
        self.temperature = temperature
        self.system_prompt = system_prompt or (
            "You are an expert bilingual Arabic-English enterprise assistant. "
            "You observe local MENA commercial customs, polite honorifics, and execute precise tool calls."
        )

    def act(
        self,
        messages: List[Message],
        tools: List[ToolDefinition],
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        try:
            import anthropic
        except ImportError:
            raise ImportError(
                "anthropic package is required to use AnthropicAgent. Install it with: pip install anthropic"
            )

        if not self.api_key:
            raise ValueError(
                "Anthropic API key must be provided via constructor or ANTHROPIC_API_KEY environment variable."
            )

        client = anthropic.Anthropic(api_key=self.api_key, base_url=self.base_url)

        claude_messages = []
        for m in messages:
            role = "user" if m.role in ("user", "human") else "assistant"
            claude_messages.append({"role": role, "content": m.content})

        claude_tools = [t.to_anthropic_schema() for t in tools] if tools else None

        kwargs: Dict[str, Any] = {
            "model": self.model_name,
            "messages": claude_messages,
            "max_tokens": 2048,
            "temperature": self.temperature,
            "system": self.system_prompt,
        }
        if claude_tools:
            kwargs["tools"] = claude_tools

        response = client.messages.create(**kwargs)
        content_text = ""
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                content_text += block.text
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        tool_name=block.name,
                        arguments=block.input if isinstance(block.input, dict) else {},
                        call_id=block.id,
                    )
                )

        metadata = {
            "id": response.id,
            "usage": response.usage.model_dump() if response.usage else {},
            "model": response.model,
        }

        return AgentResponse(message=content_text, tool_calls=tool_calls, metadata=metadata)
