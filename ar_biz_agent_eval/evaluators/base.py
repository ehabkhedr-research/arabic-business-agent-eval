from abc import ABC, abstractmethod
from typing import List, Union
from ar_biz_agent_eval.core.models import MetricScore, SessionState
from ar_biz_agent_eval.core.scenario import Scenario
from ar_biz_agent_eval.environments.base import BaseEnvironment


class BaseEvaluator(ABC):
    """Abstract base class for benchmark metric evaluators."""

    @abstractmethod
    def evaluate(
        self,
        scenario: Scenario,
        session_state: SessionState,
        environment: BaseEnvironment,
    ) -> Union[MetricScore, List[MetricScore]]:
        """Evaluate agent session performance against the scenario and environment state."""
        pass
