import json
import os
from typing import Any, Dict, List, Optional
from ar_biz_agent_eval.agents.base import AgentResponse, BaseAgent
from ar_biz_agent_eval.core.models import Message, ToolCall
from ar_biz_agent_eval.environments.base import ToolDefinition


class GeminiAgent(BaseAgent):
    """Adapter for Google Gemini models (e.g. gemini-2.0-flash, gemini-1.5-pro)."""

    def __init__(
        self,
        name: str = "Gemini-Agent",
        model_name: str = "gemini-2.0-flash",
        api_key: Optional[str] = None,
        temperature: float = 0.0,
        system_instruction: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(name=name, model_name=model_name, **kwargs)
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.temperature = temperature
        self.system_instruction = system_instruction or (
            "You are an expert bilingual Arabic-English enterprise assistant. "
            "You strictly observe local MENA commercial customs, honorifics, and execute precise tool calls."
        )

    def act(
        self,
        messages: List[Message],
        tools: List[ToolDefinition],
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            raise ImportError(
                "google-genai package is required to use GeminiAgent. Install it with: pip install google-genai"
            )

        if not self.api_key:
            raise ValueError(
                "Gemini API key must be provided via constructor or GEMINI_API_KEY / GOOGLE_API_KEY environment variables."
            )

        client = genai.Client(api_key=self.api_key)

        gemini_tools = []
        if tools:
            declarations = []
            for t in tools:
                declarations.append(
                    types.FunctionDeclaration(
                        name=t.name,
                        description=t.description,
                        parameters=t.parameters,
                    )
                )
            gemini_tools.append(types.Tool(function_declarations=declarations))

        contents = []
        for m in messages:
            role = "user" if m.role in ("user", "human") else "model"
            contents.append(types.Content(role=role, parts=[types.Part.from_text(text=m.content)]))

        config = types.GenerateContentConfig(
            temperature=self.temperature,
            system_instruction=self.system_instruction,
            tools=gemini_tools if gemini_tools else None,
        )

        response = client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=config,
        )

        content_text = response.text or ""
        tool_calls = []

        if response.function_calls:
            for fc in response.function_calls:
                args = fc.args if isinstance(fc.args, dict) else {}
                tool_calls.append(
                    ToolCall(
                        tool_name=fc.name,
                        arguments=args,
                    )
                )

        return AgentResponse(
            message=content_text,
            tool_calls=tool_calls,
            metadata={"model": self.model_name},
        )
