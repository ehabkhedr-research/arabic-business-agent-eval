from typing import Any, Dict
from ar_biz_agent_eval.core.models import MetricScore, SessionState
from ar_biz_agent_eval.core.scenario import Scenario
from ar_biz_agent_eval.environments.base import BaseEnvironment
from ar_biz_agent_eval.evaluators.base import BaseEvaluator


class EfficiencyEvaluator(BaseEvaluator):
    """Evaluates Turn & Cost Efficiency Index (TECI - Weight 0.15).
    
    Penalizes conversational drifting, excessive clarifying turns,
    and redundant duplicate tool invocations.
    
    Formula: max(0.0, 1.0 - 0.15 * max(0, actual_turns - golden_turns))
    """

    def evaluate(
        self,
        scenario: Scenario,
        session_state: SessionState,
        environment: BaseEnvironment,
    ) -> MetricScore:
        golden_turns = scenario.evaluation_criteria.golden_turn_count or len(scenario.turns)
        actual_turns = session_state.turn_count

        # Turn penalty
        turn_penalty = 0.15 * max(0, actual_turns - golden_turns)
        base_teci = max(0.0, 1.0 - turn_penalty)

        # Redundancy penalty (calling identical tool with identical args multiple times)
        seen_calls = set()
        redundant_calls = 0
        for tc in session_state.tool_calls:
            call_sig = f"{tc.tool_name}:{sorted(tc.arguments.items())}"
            if call_sig in seen_calls:
                redundant_calls += 1
            else:
                seen_calls.add(call_sig)

        redundancy_penalty = 0.10 * redundant_calls
        final_teci = round(max(0.0, min(1.0, base_teci - redundancy_penalty)), 3)

        details: Dict[str, Any] = {
            "golden_turns": golden_turns,
            "actual_turns": actual_turns,
            "redundant_calls": redundant_calls,
            "turn_penalty": round(turn_penalty, 3),
            "redundancy_penalty": round(redundancy_penalty, 3),
        }

        return MetricScore(
            name="TECI",
            score=final_teci,
            weight=0.15,
            passed=final_teci >= 0.70,
            details=details,
        )
