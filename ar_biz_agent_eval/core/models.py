"""Core data structures and runtime schemas for the evaluation framework."""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

from ar_biz_agent_eval.core.scenario import DialectEnum, DomainEnum


class ToolCall(BaseModel):
    """Represents a tool call initiated by an agent."""

    id: str = Field(default_factory=lambda: f"call_{uuid.uuid4().hex[:8]}")
    call_id: Optional[str] = None
    function_name: str = Field(default="", description="Name of the function called")
    tool_name: Optional[str] = Field(default=None, description="Alias for function_name")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Arguments passed to the tool")

    def model_post_init(self, __context: Any) -> None:
        if not self.function_name and self.tool_name:
            self.function_name = self.tool_name
        elif not self.tool_name and self.function_name:
            self.tool_name = self.function_name
        if not self.call_id and self.id:
            self.call_id = self.id
        elif not self.id and self.call_id:
            self.id = self.call_id

    @property
    def name(self) -> str:
        return self.tool_name or self.function_name


class ToolResult(BaseModel):
    """Result returned by environment after executing a tool call."""

    tool_call_id: Optional[str] = None
    call_id: Optional[str] = None
    function_name: str = ""
    tool_name: Optional[str] = None
    output: Any = None
    result: Any = None
    error: Optional[str] = None
    arguments: Dict[str, Any] = Field(default_factory=dict)
    execution_time_ms: float = 0.0
    latency_seconds: float = 0.0

    def model_post_init(self, __context: Any) -> None:
        if not self.function_name and self.tool_name:
            self.function_name = self.tool_name
        elif not self.tool_name and self.function_name:
            self.tool_name = self.function_name
        if self.output is None and self.result is not None:
            self.output = self.result
        elif self.result is None and self.output is not None:
            self.result = self.output
        if not self.call_id and self.tool_call_id:
            self.call_id = self.tool_call_id
        elif not self.tool_call_id and self.call_id:
            self.tool_call_id = self.call_id

    @property
    def success(self) -> bool:
        return self.error is None

    @property
    def data(self) -> Any:
        return self.output if self.output is not None else self.result


class Message(BaseModel):
    """A single turn message in a conversation session."""

    role: str = Field(..., description="Role: 'system', 'user', 'assistant', or 'tool'")
    content: str = Field(default="", description="Text content of the message")
    name: Optional[str] = Field(default=None, description="Optional name of the sender")
    tool_calls: List[ToolCall] = Field(default_factory=list, description="Tool calls triggered by assistant")
    tool_call_id: Optional[str] = Field(default=None, description="ID of tool call if role is 'tool'")
    timestamp: float = Field(default_factory=time.time)


class MetricScore(BaseModel):
    """Individual metric evaluation score."""

    name: str = Field(..., description="Name of the metric")
    category: str = Field(default="benchmark", description="Category: tool_calling, business_goal, cultural_safety, efficiency")
    score: float = Field(..., ge=0.0, le=1.0, description="Normalized score between 0.0 and 1.0")
    weight: float = Field(default=1.0, ge=0.0, description="Weight in overall aggregation")
    passed: bool = Field(default=True, description="Whether metric met the passing threshold")
    rationale: str = Field(default="", description="Detailed explanation of the score")
    details: Dict[str, Any] = Field(default_factory=dict, description="Structured diagnostics")


class SessionState(BaseModel):
    """Mutable runtime session state tracking conversation and environment."""

    scenario_id: str
    agent_name: str = "agent"
    model_name: str = "default"
    turn_index: int = 0
    conversation: List[Message] = Field(default_factory=list)
    environment_state: Dict[str, Any] = Field(default_factory=dict)
    tool_history: List[ToolResult] = Field(default_factory=list)
    pending_tool_calls: List[ToolCall] = Field(default_factory=list)
    completed: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def messages(self) -> List[Message]:
        return self.conversation

    @property
    def tool_calls(self) -> List[ToolResult]:
        return self.tool_history

    @property
    def turn_count(self) -> int:
        asst_count = sum(1 for m in self.conversation if m.role == "assistant")
        return max(self.turn_index, asst_count)

    def add_message(
        self,
        role_or_msg: Union[str, Message],
        content: str = "",
        tool_calls: Optional[List[ToolCall]] = None,
        tool_call_id: Optional[str] = None,
    ) -> Message:
        if isinstance(role_or_msg, Message):
            msg = role_or_msg
        else:
            msg = Message(
                role=role_or_msg,
                content=content,
                tool_calls=tool_calls or [],
                tool_call_id=tool_call_id,
            )
        self.conversation.append(msg)
        return msg

    def record_tool_call(self, result: ToolResult) -> None:
        self.tool_history.append(result)
        output_str = str(result.output) if result.output is not None else (result.error or "")
        cid = result.tool_call_id or result.call_id or f"call_{len(self.tool_history)}"
        self.add_message(
            role_or_msg="tool",
            content=output_str,
            tool_call_id=cid,
        )

    def record_tool_result(self, result: ToolResult) -> None:
        self.record_tool_call(result)


class EvaluationResult(BaseModel):
    """Comprehensive evaluation result for a single scenario run."""

    scenario_id: str
    scenario_title: str = ""
    domain: Union[str, DomainEnum] = ""
    dialect: Union[str, DialectEnum] = ""
    passed: bool = False
    overall_score: float = 0.0
    metric_scores: List[MetricScore] = Field(default_factory=list)
    metrics: List[MetricScore] = Field(default_factory=list)
    session_state: Optional[SessionState] = None
    total_turns: int = 0
    tool_calls_count: int = 0
    execution_time_s: float = 0.0
    messages: List[Message] = Field(default_factory=list)
    tool_history: List[ToolResult] = Field(default_factory=list)
    final_environment_state: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None

    def model_post_init(self, __context: Any) -> None:
        if not self.metrics and self.metric_scores:
            self.metrics = self.metric_scores
        elif not self.metric_scores and self.metrics:
            self.metric_scores = self.metrics

    def get_metric(self, name: str) -> Optional[MetricScore]:
        for m in self.metric_scores:
            if m.name == name:
                return m
        return None

    def calculate_weighted_score(self) -> float:
        scores = self.metric_scores or self.metrics
        if not scores:
            return 0.0
        total_weight = sum(m.weight for m in scores)
        if total_weight <= 0.0:
            return 0.0
        weighted_sum = sum(m.score * m.weight for m in scores)
        return round(weighted_sum / total_weight, 4)
