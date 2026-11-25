"""Registries for benchmark scenarios, evaluators, and agent adapters."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional
from ar_biz_agent_eval.core.scenario import DialectEnum, DomainEnum, Scenario


class ScenarioRegistry:
    """Registry of benchmark scenarios with both instance and class methods."""

    def __init__(self) -> None:
        self._scenarios: Dict[str, Scenario] = {}

    def register(self, scenario: Scenario) -> None:
        """Register a scenario instance."""
        self._scenarios[scenario.id] = scenario

    def get(self, scenario_id: str) -> Optional[Scenario]:
        """Get a scenario by ID."""
        return self._scenarios.get(scenario_id)

    def list_all(self) -> List[Scenario]:
        """List all registered scenarios."""
        return list(self._scenarios.values())

    def count(self) -> int:
        """Count registered scenarios."""
        return len(self._scenarios)

    def filter(
        self,
        dialect: Optional[DialectEnum | str] = None,
        domain: Optional[DomainEnum | str] = None,
        difficulty: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> List[Scenario]:
        """Filter scenarios by metadata attributes."""
        results = list(self._scenarios.values())
        if dialect:
            dialect_val = dialect.value if isinstance(dialect, DialectEnum) else str(dialect).lower()
            results = [
                s for s in results
                if (s.dialect.value if isinstance(s.dialect, DialectEnum) else str(s.dialect).lower()) == dialect_val
            ]
        if domain:
            domain_val = domain.value if isinstance(domain, DomainEnum) else str(domain).lower()
            results = [
                s for s in results
                if (s.domain.value if isinstance(s.domain, DomainEnum) else str(s.domain).lower()) == domain_val
            ]
        if difficulty:
            results = [s for s in results if s.difficulty.lower() == difficulty.lower()]
        if tag:
            results = [s for s in results if s.tags and tag in s.tags]
        return results

    def clear(self) -> None:
        """Clear the registry."""
        self._scenarios.clear()


class EvaluatorRegistry:
    """Registry for pluggable evaluator classes."""

    def __init__(self) -> None:
        self._evaluators: Dict[str, Any] = {}

    def register(self, name: str, evaluator_cls: Any) -> None:
        self._evaluators[name] = evaluator_cls

    def get(self, name: str) -> Optional[Any]:
        return self._evaluators.get(name)

    def list_all(self) -> Dict[str, Any]:
        return dict(self._evaluators)

    def count(self) -> int:
        return len(self._evaluators)

    def clear(self) -> None:
        self._evaluators.clear()


class AgentRegistry:
    """Registry for agent adapters."""

    def __init__(self) -> None:
        self._agents: Dict[str, Any] = {}

    def register(self, name: str, agent_cls: Any) -> None:
        self._agents[name] = agent_cls

    def get(self, name: str) -> Optional[Any]:
        return self._agents.get(name)

    def list_all(self) -> Dict[str, Any]:
        return dict(self._agents)

    def count(self) -> int:
        return len(self._agents)

    def clear(self) -> None:
        self._agents.clear()


# Global Singleton Registries
scenario_registry = ScenarioRegistry()
evaluator_registry = EvaluatorRegistry()
agent_registry = AgentRegistry()
