import json
from typing import Any, Dict, List, Optional
import urllib.request
import urllib.error
from ar_biz_agent_eval.agents.base import AgentResponse, BaseAgent
from ar_biz_agent_eval.core.models import Message, ToolCall
from ar_biz_agent_eval.environments.base import ToolDefinition


class HttpA2AAgent(BaseAgent):
    """Generic HTTP / Agent-to-Agent (A2A) adapter connecting to custom endpoints or remote microservices."""

    def __init__(
        self,
        name: str = "HTTP-A2A-Agent",
        endpoint: str = "http://localhost:8000/agent/act",
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 30.0,
        **kwargs,
    ):
        super().__init__(name=name, model_name=f"http-endpoint:{endpoint}", **kwargs)
        self.endpoint = endpoint
        self.headers = headers or {"Content-Type": "application/json"}
        self.timeout = timeout

    def act(
        self,
        messages: List[Message],
        tools: List[ToolDefinition],
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        payload = {
            "messages": [m.model_dump() for m in messages],
            "tools": [t.to_openai_schema() for t in tools],
            "context": context or {},
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.endpoint, data=data, headers=self.headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            raise RuntimeError(f"Failed to communicate with A2A endpoint at {self.endpoint}: {e}")

        msg = resp_data.get("message", "")
        raw_tool_calls = resp_data.get("tool_calls", [])
        tool_calls = [
            ToolCall(
                tool_name=tc.get("tool_name") or tc.get("name"),
                arguments=tc.get("arguments") or tc.get("args") or {},
                call_id=tc.get("call_id") or tc.get("id"),
            )
            for tc in raw_tool_calls
        ]

        return AgentResponse(
            message=msg,
            tool_calls=tool_calls,
            metadata=resp_data.get("metadata", {}),
        )
