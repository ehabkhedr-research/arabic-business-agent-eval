from typing import Any, Dict, List
from ar_biz_agent_eval.core.models import MetricScore, SessionState
from ar_biz_agent_eval.core.scenario import Scenario
from ar_biz_agent_eval.environments.base import BaseEnvironment
from ar_biz_agent_eval.evaluators.base import BaseEvaluator


class ToolCallEvaluator(BaseEvaluator):
    """Evaluates Action Validity Rate (AVR - Weight 0.20) and Parameter Extraction Accuracy (PEA - Weight 0.20)."""

    def evaluate(
        self,
        scenario: Scenario,
        session_state: SessionState,
        environment: BaseEnvironment,
    ) -> List[MetricScore]:
        available_tools = {t.name for t in environment.get_tools()}
        actual_calls = session_state.tool_calls

        expected_calls = []
        for turn in scenario.turns:
            expected_calls.extend(turn.expected_tool_calls)

        # 1. Action Validity Rate (AVR)
        if not actual_calls:
            avr_score = 1.0 if not expected_calls else 0.0
            avr_details = {"total_calls": 0, "expected_calls": len(expected_calls)}
        else:
            valid_count = 0
            for tc in actual_calls:
                # Valid tool name and executed without syntax/schema validation error
                if tc.tool_name in available_tools and tc.error is None:
                    valid_count += 1
            avr_score = round(valid_count / len(actual_calls), 3)
            avr_details = {
                "total_calls": len(actual_calls),
                "valid_calls": valid_count,
                "invalid_tools": [tc.tool_name for tc in actual_calls if tc.tool_name not in available_tools],
            }

        avr_metric = MetricScore(
            name="AVR",
            score=avr_score,
            weight=0.20,
            passed=avr_score >= 0.8,
            details=avr_details,
        )

        # 2. Parameter Extraction Accuracy (PEA)
        if not expected_calls:
            pea_score = 1.0
            pea_details = {"message": "No specific tool calls expected."}
        elif not actual_calls:
            pea_score = 0.0
            pea_details = {"message": "No tool calls executed by agent."}
        else:
            total_expected_args = 0
            total_actual_args = 0
            matched_args = 0

            # Match actual calls to expected calls by tool name
            unmatched_actual = list(actual_calls)
            for exp in expected_calls:
                exp_args = exp.arguments
                total_expected_args += len(exp_args)

                # Find best matching actual call
                best_match = None
                for act in unmatched_actual:
                    if act.tool_name == exp.tool_name or act.tool_name.endswith(exp.tool_name) or exp.tool_name.endswith(act.tool_name):
                        best_match = act
                        break

                if best_match:
                    unmatched_actual.remove(best_match)
                    total_actual_args += len(best_match.arguments)
                    for k, exp_val in exp_args.items():
                        if k in best_match.arguments:
                            act_val = best_match.arguments[k]
                            if self._values_match(exp_val, act_val):
                                matched_args += 1
                else:
                    # No match for this expected call
                    pass

            for remaining in unmatched_actual:
                total_actual_args += len(remaining.arguments)

            precision = matched_args / total_actual_args if total_actual_args > 0 else 0.0
            recall = matched_args / total_expected_args if total_expected_args > 0 else 0.0
            if (precision + recall) > 0:
                f1 = 2 * (precision * recall) / (precision + recall)
            else:
                f1 = 0.0

            pea_score = round(f1, 3)
            pea_details = {
                "matched_args": matched_args,
                "total_expected_args": total_expected_args,
                "total_actual_args": total_actual_args,
                "precision": round(precision, 3),
                "recall": round(recall, 3),
                "f1": pea_score,
            }

        pea_metric = MetricScore(
            name="PEA",
            score=pea_score,
            weight=0.20,
            passed=pea_score >= 0.75,
            details=pea_details,
        )

        return [avr_metric, pea_metric]

    def _values_match(self, v1: Any, v2: Any) -> bool:
        if v1 == v2:
            return True
        from ar_biz_agent_eval.core.unicode_utils import clean_for_comparison, convert_arabic_digits
        # String comparison with Arabic orthographic and digit normalization
        if isinstance(v1, str) and isinstance(v2, str):
            if v1.strip().lower() == v2.strip().lower():
                return True
            return clean_for_comparison(v1) == clean_for_comparison(v2)
        # Numeric approximate comparison (handling possible Eastern Arabic numeral strings)
        if isinstance(v1, (int, float)) or isinstance(v2, (int, float)):
            try:
                n1 = float(convert_arabic_digits(str(v1))) if isinstance(v1, str) else float(v1)
                n2 = float(convert_arabic_digits(str(v2))) if isinstance(v2, str) else float(v2)
                return abs(n1 - n2) < 0.01
            except (ValueError, TypeError):
                pass
        # List comparison
        if isinstance(v1, list) and isinstance(v2, list):
            return len(v1) == len(v2)
        return False
