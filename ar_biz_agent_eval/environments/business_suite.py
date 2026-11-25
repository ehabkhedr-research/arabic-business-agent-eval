"""Unified MENA Business Suite Environment consolidating CRM, ERP, Billing & Support."""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional
from ar_biz_agent_eval.environments.base import BaseEnvironment
from ar_biz_agent_eval.environments.mock_crm import MockCRMEnvironment
from ar_biz_agent_eval.environments.mock_erp import MockERPEnvironment
from ar_biz_agent_eval.environments.mock_billing import MockBillingEnvironment
from ar_biz_agent_eval.environments.mock_support import MockSupportEnvironment


class BusinessEnvironment(BaseEnvironment):
    """Unified environment bundling CRM, ERP, Billing (ZATCA/VAT), and Support tools."""

    def __init__(self, initial_state: Optional[Dict[str, Any]] = None):
        # Instantiate sub-environments to borrow their tool definitions and handlers
        self.crm_env = MockCRMEnvironment()
        self.erp_env = MockERPEnvironment()
        self.billing_env = MockBillingEnvironment()
        self.support_env = MockSupportEnvironment()

        unified_initial: Dict[str, Any] = {}
        unified_initial.update(copy.deepcopy(self.crm_env.state))
        unified_initial.update(copy.deepcopy(self.erp_env.state))
        unified_initial.update(copy.deepcopy(self.billing_env.state))
        unified_initial.update(copy.deepcopy(self.support_env.state))

        if initial_state:
            unified_initial.update(copy.deepcopy(initial_state))

        super().__init__(initial_state=unified_initial)

        # Wire sub-environments to share the unified state object
        self.crm_env.state = self.state
        self.erp_env.state = self.state
        self.billing_env.state = self.state
        self.support_env.state = self.state

    @property
    def crm(self) -> MockCRMEnvironment:
        return self.crm_env

    @property
    def erp(self) -> MockERPEnvironment:
        return self.erp_env

    @property
    def billing(self) -> MockBillingEnvironment:
        return self.billing_env

    @property
    def support(self) -> MockSupportEnvironment:
        return self.support_env

    def _setup_tools(self) -> None:
        # Register CRM tools
        for tool_def in self.crm_env.list_tools():
            handler = getattr(self.crm_env, tool_def.name, None)
            if handler:
                self.register_tool(tool_def, handler)

        # Register ERP tools
        for tool_def in self.erp_env.list_tools():
            handler = getattr(self.erp_env, tool_def.name, None)
            if handler:
                self.register_tool(tool_def, handler)

        # Register Billing tools
        for tool_def in self.billing_env.list_tools():
            handler = getattr(self.billing_env, tool_def.name, None)
            if handler:
                self.register_tool(tool_def, handler)

        # Register Support tools
        for tool_def in self.support_env.list_tools():
            handler = getattr(self.support_env, tool_def.name, None)
            if handler:
                self.register_tool(tool_def, handler)

    def reset(self) -> None:
        super().reset()
        self.crm_env.state = self.state
        self.erp_env.state = self.state
        self.billing_env.state = self.state
        self.support_env.state = self.state
