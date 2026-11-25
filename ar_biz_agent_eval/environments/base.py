"""Base classes for mock business environments and tools."""

from __future__ import annotations

import copy
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from ar_biz_agent_eval.core.models import ToolCall, ToolResult


class ResultDict(dict):
    """Dictionary subclass supporting attribute access for .success, .data, .error, and keys."""

    @property
    def success(self) -> bool:
        val = self.get("success")
        if val is not None:
            return bool(val)
        return "error" not in self or not self.get("error")

    @property
    def data(self) -> Dict[str, Any]:
        return self

    @property
    def error(self) -> Optional[str]:
        return self.get("error")

    def __getattr__(self, name: str) -> Any:
        if name in self:
            return self[name]
        raise AttributeError(f"'ResultDict' object has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value


class ToolParameter(BaseModel):
    """Parameter definition for an environment tool."""

    name: str
    type: str = "string"  # string, integer, number, boolean, array, object
    description: str = ""
    required: bool = True
    default: Optional[Any] = None
    enum: Optional[List[str]] = None


class ToolDefinition(BaseModel):
    """Formal tool definition exposing OpenAI / Anthropic function calling schemas."""

    name: str
    description: str
    parameters: List[ToolParameter] = Field(default_factory=list)
    handler: Optional[Callable[..., Any]] = None

    def to_openai_schema(self) -> Dict[str, Any]:
        properties: Dict[str, Any] = {}
        required: List[str] = []

        for p in self.parameters:
            prop: Dict[str, Any] = {"type": p.type, "description": p.description}
            if p.enum:
                prop["enum"] = p.enum
            properties[p.name] = prop
            if p.required:
                required.append(p.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }

    def to_anthropic_schema(self) -> Dict[str, Any]:
        properties: Dict[str, Any] = {}
        required: List[str] = []

        for p in self.parameters:
            prop: Dict[str, Any] = {"type": p.type, "description": p.description}
            if p.enum:
                prop["enum"] = p.enum
            properties[p.name] = prop
            if p.required:
                required.append(p.name)

        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }


class BaseEnvironment:
    """Abstract base class for stateful mock business environments."""

    def __init__(self, initial_state: Optional[Dict[str, Any]] = None):
        self._initial_state = copy.deepcopy(initial_state) if initial_state else {}
        self.state: Dict[str, Any] = copy.deepcopy(self._initial_state)
        self._tools: Dict[str, Callable[..., Any]] = {}
        self._tool_definitions: Dict[str, ToolDefinition] = {}
        self.execution_history: List[ToolResult] = []
        self._setup_tools()

    def _setup_tools(self) -> None:
        """Register tool methods and definitions. Subclasses must implement."""
        pass

    def register_tool(self, definition: ToolDefinition, func: Callable[..., Any]) -> None:
        """Register a tool and its implementation."""
        self._tools[definition.name] = func
        self._tool_definitions[definition.name] = definition

    def list_tools(self) -> List[ToolDefinition]:
        """Return all registered tool definitions."""
        return list(self._tool_definitions.values())

    def get_tools(self) -> List[ToolDefinition]:
        """Alias for list_tools."""
        return self.list_tools()

    def get_tool_definition(self, name: str) -> Optional[ToolDefinition]:
        """Get definition for a specific tool."""
        return self._tool_definitions.get(name)

    def execute_tool(
        self,
        tool_call_or_name: Union[ToolCall, str],
        arguments: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> ToolResult:
        """Execute a tool call safely, measure latency, and track execution."""
        start_time = time.perf_counter()

        if isinstance(tool_call_or_name, ToolCall):
            name = tool_call_or_name.function_name or tool_call_or_name.tool_name or ""
            args = tool_call_or_name.arguments
            call_id = tool_call_or_name.id or tool_call_or_name.call_id or f"call_{uuid.uuid4().hex[:8]}"
        else:
            name = tool_call_or_name
            args = arguments if arguments is not None else kwargs
            call_id = f"call_{uuid.uuid4().hex[:8]}"

        func = self._tools.get(name)
        if not func:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            res = ToolResult(
                tool_call_id=call_id,
                function_name=name,
                tool_name=name,
                arguments=args,
                output=None,
                error=f"Error: Unknown tool '{name}'. Available: {list(self._tools.keys())}",
                execution_time_ms=elapsed_ms,
                latency_seconds=elapsed_ms / 1000.0,
            )
            self.execution_history.append(res)
            return res

        try:
            output = func(**args)
            if isinstance(output, dict) and not isinstance(output, ResultDict):
                output = ResultDict(output)

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            res = ToolResult(
                tool_call_id=call_id,
                function_name=name,
                tool_name=name,
                arguments=args,
                output=output,
                result=output,
                error=None,
                execution_time_ms=elapsed_ms,
                latency_seconds=elapsed_ms / 1000.0,
            )
            self.execution_history.append(res)
            return res
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            res = ToolResult(
                tool_call_id=call_id,
                function_name=name,
                tool_name=name,
                arguments=args,
                output=None,
                error=f"Execution error in {name}: {str(e)}",
                execution_time_ms=elapsed_ms,
                latency_seconds=elapsed_ms / 1000.0,
            )
            self.execution_history.append(res)
            return res

    def reset(self) -> None:
        """Reset state back to initial."""
        self.state = copy.deepcopy(self._initial_state)
        self.execution_history.clear()
