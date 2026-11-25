import json
import os
from typing import Any, Dict, List, Optional
from ar_biz_agent_eval.agents.base import AgentResponse, BaseAgent
from ar_biz_agent_eval.core.models import Message, ToolCall
from ar_biz_agent_eval.environments.base import ToolDefinition


class OpenAIAgent(BaseAgent):
    """Adapter for OpenAI models (e.g. gpt-4o, gpt-4o-mini) using function calling."""

    def __init__(
        self,
        name: str = "OpenAI-Agent",
        model_name: str = "gpt-4o",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.0,
        system_prompt: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(name=name, model_name=model_name, **kwargs)
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")
        self.temperature = temperature
        self.system_prompt = system_prompt or (
            "You are an expert bilingual Arabic-English enterprise assistant. "
            "You follow local MENA business customs, polite honorifics, and execute precise tool calls."
        )

    def act(
        self,
        messages: List[Message],
        tools: List[ToolDefinition],
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "openai package is required to use OpenAIAgent. Install it with: pip install openai"
            )

        if not self.api_key:
            raise ValueError(
                "OpenAI API key must be provided either via constructor or OPENAI_API_KEY environment variable."
            )

        client = OpenAI(api_key=self.api_key, base_url=self.base_url)

        openai_messages = [{"role": "system", "content": self.system_prompt}]
        for m in messages:
            msg_dict = {"role": m.role, "content": m.content}
            if m.tool_call_id:
                msg_dict["tool_call_id"] = m.tool_call_id
            openai_messages.append(msg_dict)

        openai_tools = [t.to_openai_schema() for t in tools] if tools else None

        kwargs: Dict[str, Any] = {
            "model": self.model_name,
            "messages": openai_messages,
            "temperature": self.temperature,
        }
        if openai_tools:
            kwargs["tools"] = openai_tools

        response = client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        content = choice.message.content or ""
        tool_calls = []

        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                arguments = {}
                if tc.function.arguments:
                    try:
                        arguments = json.loads(tc.function.arguments)
                    except Exception:
                        arguments = {"raw": tc.function.arguments}
                tool_calls.append(
                    ToolCall(
                        tool_name=tc.function.name,
                        arguments=arguments,
                        call_id=tc.id,
                    )
                )

        metadata = {
            "id": response.id,
            "usage": response.usage.model_dump() if response.usage else {},
            "model": response.model,
        }

        return AgentResponse(message=content, tool_calls=tool_calls, metadata=metadata)
