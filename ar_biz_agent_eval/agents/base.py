from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from ar_biz_agent_eval.core.models import Message, ToolCall
from ar_biz_agent_eval.environments.base import ToolDefinition


class AgentResponse(BaseModel):
    """Structured response returned by an agent in a turn."""
    message: str = Field(..., description="Conversational natural language message in Arabic or English")
    tool_calls: List[ToolCall] = Field(default_factory=list, description="Tool calls issued by the agent")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Diagnostic metadata (e.g. latency, token usage)")


class BaseAgent(ABC):
    """Abstract base class for agents participating in the Arabic business evaluation benchmark."""

    def __init__(self, name: str, model_name: str = "generic-agent", **kwargs):
        self.name = name
        self.model_name = model_name
        self.config = kwargs

    @abstractmethod
    def act(
        self,
        messages: List[Message],
        tools: List[ToolDefinition],
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        """Process conversation history and available tools, returning an AgentResponse.
        
        Args:
            messages: Full conversation history of the session.
            tools: Definitions of available tools in the business environment.
            context: Optional contextual information (e.g. active scenario metadata).
        """
        pass

    def reset(self) -> None:
        """Reset internal agent state between scenarios."""
        pass
