from typing import Any, Dict, List
from ar_biz_agent_eval.core.models import MetricScore, SessionState
from ar_biz_agent_eval.core.scenario import Scenario, StateAssertion
from ar_biz_agent_eval.environments.base import BaseEnvironment
from ar_biz_agent_eval.evaluators.base import BaseEvaluator


class BusinessGoalEvaluator(BaseEvaluator):
    """Evaluates Goal and State Completion Rate (GSCR - Weight 0.30).
    
    Verifies that real business side-effects occurred in the environment,
    such as database updates, purchase orders created, invoices generated,
    or tickets updated, according to scenario state assertions.
    """

    def evaluate(
        self,
        scenario: Scenario,
        session_state: SessionState,
        environment: BaseEnvironment,
    ) -> MetricScore:
        assertions = scenario.state_assertions or []
        details: Dict[str, Any] = {"checked_assertions": [], "passed_count": 0, "total_count": len(assertions)}

        if not assertions:
            # Fallback: Check if expected tools were executed without errors
            expected_tools = []
            for t in scenario.turns:
                for exp in t.expected_tool_calls:
                    expected_tools.append(exp.tool_name)

            actual_tool_names = [tr.tool_name for tr in session_state.tool_calls if not tr.error]
            if not expected_tools:
                return MetricScore(
                    name="GSCR",
                    score=1.0,
                    weight=0.30,
                    passed=True,
                    details={"message": "No state assertions or expected tools required."},
                )

            matched = sum(1 for exp in expected_tools if exp in actual_tool_names)
            score = round(matched / len(expected_tools), 3)
            return MetricScore(
                name="GSCR",
                score=score,
                weight=0.30,
                passed=score >= 0.8,
                details={"matched_tools": matched, "expected_tools": expected_tools},
            )

        passed_count = 0
        for assertion in assertions:
            is_pass, reason = self._check_assertion(assertion, environment)
            details["checked_assertions"].append(
                {
                    "entity": assertion.entity,
                    "target_id": assertion.target_id,
                    "field": assertion.field,
                    "expected": assertion.expected_value,
                    "passed": is_pass,
                    "reason": reason,
                }
            )
            if is_pass:
                passed_count += 1

        details["passed_count"] = passed_count
        score = round(passed_count / len(assertions), 3) if assertions else 1.0

        return MetricScore(
            name="GSCR",
            score=score,
            weight=0.30,
            passed=score >= 0.8,
            details=details,
        )

    def _check_assertion(
        self, assertion: StateAssertion, environment: BaseEnvironment
    ) -> tuple[bool, str]:
        # Search the environment services for target entity
        target_obj = None

        # Check CRM
        if hasattr(environment, "crm"):
            crm = environment.crm
            if assertion.entity == "lead" and assertion.target_id in crm.leads:
                target_obj = crm.leads[assertion.target_id]
            elif assertion.entity == "deal" and assertion.target_id in crm.deals:
                target_obj = crm.deals[assertion.target_id]

        # Check ERP
        if hasattr(environment, "erp"):
            erp = environment.erp
            if assertion.entity == "purchase_order" and assertion.target_id in erp.purchase_orders:
                target_obj = erp.purchase_orders[assertion.target_id]
            elif assertion.entity == "inventory_reservation":
                target_obj = erp.inventory_reservations.get(assertion.target_id)

        # Check Billing
        if hasattr(environment, "billing"):
            billing = environment.billing
            if assertion.entity == "invoice" and assertion.target_id in billing.invoices:
                target_obj = billing.invoices[assertion.target_id]
            elif assertion.entity == "tax_invoice":
                for inv in billing.invoices.values():
                    if inv.get("customer_vat_number") == assertion.target_id or inv.get("invoice_id") == assertion.target_id:
                        target_obj = inv
                        break

        # Check Support
        if hasattr(environment, "support"):
            support = environment.support
            if assertion.entity == "ticket" and assertion.target_id in support.tickets:
                target_obj = support.tickets[assertion.target_id]
            elif assertion.entity == "refund":
                for ref in support.refunds:
                    if ref.get("ticket_id") == assertion.target_id:
                        target_obj = ref
                        break

        if target_obj is None:
            # Check if any items exist matching entity type when target_id is wildcard or last created
            if assertion.target_id == "*" or assertion.target_id is None:
                if assertion.entity == "tax_invoice" and hasattr(environment, "billing") and environment.billing.invoices:
                    target_obj = list(environment.billing.invoices.values())[-1]
                elif assertion.entity == "purchase_order" and hasattr(environment, "erp") and environment.erp.purchase_orders:
                    target_obj = list(environment.erp.purchase_orders.values())[-1]

        if target_obj is None:
            return False, f"Entity {assertion.entity} with ID {assertion.target_id} not found in environment."

        val = getattr(target_obj, assertion.field, None) if not isinstance(target_obj, dict) else target_obj.get(assertion.field)

        op = assertion.operator
        if op == "==":
            passed = (val == assertion.expected_value)
        elif op == "!=":
            passed = (val != assertion.expected_value)
        elif op == ">=":
            passed = (val is not None and val >= assertion.expected_value)
        elif op == "<=":
            passed = (val is not None and val <= assertion.expected_value)
        elif op == "contains":
            passed = (val is not None and assertion.expected_value in val)
        else:
            passed = (val == assertion.expected_value)

        reason = f"Actual '{val}' {op} Expected '{assertion.expected_value}' -> {passed}"
        return passed, reason
