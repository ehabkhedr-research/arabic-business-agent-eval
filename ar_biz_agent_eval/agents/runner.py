import time
from typing import Any, Dict, List, Optional
from ar_biz_agent_eval.agents.base import BaseAgent
from ar_biz_agent_eval.core.models import Message, SessionState, ToolCall, ToolResult
from ar_biz_agent_eval.core.scenario import Scenario
from ar_biz_agent_eval.environments.base import BaseEnvironment
from ar_biz_agent_eval.environments.business_suite import BusinessEnvironment


class EvaluationRunner:
    """Orchestrates multi-turn evaluation sessions between an Agent and a BusinessEnvironment."""

    def __init__(self, max_tool_iterations_per_turn: int = 5):
        self.max_tool_iterations_per_turn = max_tool_iterations_per_turn

    def run_scenario(
        self,
        scenario: Scenario,
        agent: BaseAgent,
        environment: Optional[BaseEnvironment] = None,
    ) -> SessionState:
        """Run an end-to-end evaluation session for a specific scenario."""
        if environment is None:
            environment = BusinessEnvironment()

        # Apply initial environment state if specified by scenario
        if scenario.initial_state:
            for svc_name, svc_state in scenario.initial_state.items():
                if hasattr(environment, svc_name):
                    svc = getattr(environment, svc_name)
                    for k, v in svc_state.items():
                        if hasattr(svc, k):
                            setattr(svc, k, v)

        session = SessionState(
            scenario_id=scenario.id,
            agent_name=agent.name,
            model_name=agent.model_name,
        )
        agent.reset()

        tools = environment.get_tools()

        for turn_idx, turn in enumerate(scenario.turns):
            # 1. User Turn
            user_msg = Message(role="user", content=turn.user_message)
            session.add_message(user_msg)

            # 2. Agent Turn Loop (allows multi-step tool calls if needed)
            turn_context = {
                "turn_index": turn_idx,
                "expected_turn": turn,
                "dialect": scenario.dialect.value,
                "domain": scenario.domain.value,
                "scenario": scenario,
                "cultural_rubric": scenario.cultural_rubric,
            }

            for iteration in range(self.max_tool_iterations_per_turn):
                start_time = time.time()
                response = agent.act(session.messages, tools, context=turn_context)
                latency = round(time.time() - start_time, 4)

                agent_msg = Message(role="assistant", content=response.message)
                session.add_message(agent_msg)

                if not response.tool_calls:
                    # Agent concluded conversational response
                    break

                # Execute tool calls in the environment
                for tc in response.tool_calls:
                    exec_result = environment.execute_tool(tc.tool_name, tc.arguments)
                    tool_res = ToolResult(
                        tool_name=tc.tool_name,
                        arguments=tc.arguments,
                        result=exec_result.data if exec_result.success else None,
                        error=exec_result.error,
                        call_id=tc.call_id,
                        latency_seconds=latency,
                    )
                    session.record_tool_call(tool_res)

                    # Append tool result to conversation history for agent feedback
                    tool_feedback_msg = Message(
                        role="tool",
                        content=str(exec_result.data or exec_result.error),
                        tool_call_id=tc.call_id,
                    )
                    session.add_message(tool_feedback_msg)

                # If this was mock agent or turn concluded, break loop
                if getattr(agent, "mode", None) in ("golden", "blunt_refusal", "faulty_params", "hallucinated_tool"):
                    break

        return session
