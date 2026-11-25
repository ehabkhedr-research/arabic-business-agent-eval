import re
from typing import Any, Dict, List, Optional
from ar_biz_agent_eval.agents.base import AgentResponse, BaseAgent
from ar_biz_agent_eval.core.models import Message, ToolCall
from ar_biz_agent_eval.environments.base import ToolDefinition


class MockAgent(BaseAgent):
    """Deterministic Mock Agent for offline benchmarking, validation, and testing.
    
    Modes:
      - 'golden': Perfectly adheres to expected tools and parameters with respectful Arabic business etiquette.
      - 'faulty_params': Calls the right tool but corrupts parameters to test validation logic.
      - 'blunt_refusal': Violates cultural etiquette and refuses service without calling tools.
      - 'hallucinated_tool': Invokes non-existent tools to test AVR failure.
      - 'excessive_turns': Takes extra turns without taking action, harming TECI score.
    """

    def __init__(
        self,
        name: str = "Deterministic-Mock-Agent",
        mode: str = "golden",
        model_name: str = "mock-v1",
        **kwargs,
    ):
        super().__init__(name=name, model_name=model_name, **kwargs)
        self.mode = mode
        self.turn_counter = 0

    def reset(self) -> None:
        self.turn_counter = 0

    def act(
        self,
        messages: List[Message],
        tools: List[ToolDefinition],
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        self.turn_counter += 1
        last_user_msg = ""
        for m in reversed(messages):
            if m.role == "user":
                last_user_msg = m.content
                break

        # Check if golden scenario information is available in context
        expected_tool_calls = []
        if context and "expected_turn" in context:
            turn_obj = context["expected_turn"]
            expected_tool_calls = getattr(turn_obj, "expected_tool_calls", [])

        if self.mode == "blunt_refusal":
            return AgentResponse(
                message="هذه ليست مشكلتي، ولا أستطيع خدمتك حالياً. راجع الشروط بنفسك.",
                tool_calls=[],
                metadata={"mode": self.mode, "simulated": True},
            )

        if self.mode == "hallucinated_tool":
            return AgentResponse(
                message="أهلاً بك، سأقوم بتنفيذ طلبك عبر النظام الآلي.",
                tool_calls=[
                    ToolCall(
                        tool_name="unregistered_magic_resolver",
                        arguments={"client_request": last_user_msg, "priority": "instant"},
                    )
                ],
                metadata={"mode": self.mode, "simulated": True},
            )

        if self.mode == "excessive_turns" and self.turn_counter < 3:
            return AgentResponse(
                message="أهلاً بك يا فندم. هل يمكنك تأكيد التفاصيل مرة أخرى للمراجعة؟",
                tool_calls=[],
                metadata={"mode": self.mode, "simulated": True},
            )

        # Mode: 'faulty_params'
        if self.mode == "faulty_params":
            calls = []
            if expected_tool_calls:
                for exp in expected_tool_calls:
                    corrupted_args = dict(exp.arguments)
                    # Corrupt arguments: clear mandatory keys or invert numbers
                    for k in list(corrupted_args.keys()):
                        if isinstance(corrupted_args[k], (int, float)):
                            corrupted_args[k] = -9999
                        elif isinstance(corrupted_args[k], str):
                            corrupted_args[k] = "INVALID_CORRUPTED_VALUE"
                    calls.append(ToolCall(tool_name=exp.tool_name, arguments=corrupted_args))
            else:
                calls.append(
                    ToolCall(tool_name="search_leads", arguments={"invalid_filter": "error"})
                )
            return AgentResponse(
                message="حياك الله طال عمرك، جاري فحص البيانات عبر النظام.",
                tool_calls=calls,
                metadata={"mode": self.mode, "simulated": True},
            )

        # Mode: 'golden' (Perfect execution)
        calls = []
        if expected_tool_calls:
            for exp in expected_tool_calls:
                calls.append(ToolCall(tool_name=exp.tool_name, arguments=dict(exp.arguments)))
        else:
            # Rule-based heuristics if no explicit golden expectation in turn context
            calls = self._infer_tools_from_text(last_user_msg, tools)

        greeting = self._generate_culturally_appropriate_response(last_user_msg, calls, context)
        return AgentResponse(
            message=greeting,
            tool_calls=calls,
            metadata={"mode": self.mode, "simulated": True, "turn": self.turn_counter},
        )

    def _infer_tools_from_text(self, text: str, tools: List[ToolDefinition]) -> List[ToolCall]:
        """Heuristic fallback to identify intended tool from user Arabic text."""
        available_names = {t.name for t in tools}
        calls = []

        # ZATCA / Tax invoice
        if any(w in text for w in ["فاتورة", "ضريبة", "ZATCA", "زاتكا", "ضريبية"]):
            if "generate_tax_invoice" in available_names or "billing_generate_tax_invoice" in available_names:
                t_name = "generate_tax_invoice" if "generate_tax_invoice" in available_names else "billing_generate_tax_invoice"
                calls.append(
                    ToolCall(
                        tool_name=t_name,
                        arguments={
                            "customer_name": "شركة الخليج للتطوير",
                            "customer_vat_number": "300000000000003",
                            "items": [{"name": "استشارات رقمية", "quantity": 1, "unit_price": 50000.0}],
                            "currency": "SAR",
                        },
                    )
                )

        # Lead / CRM
        elif any(w in text for w in ["عميل", "مهتم", "lead", "تواصل", "سجل"]):
            if "create_lead" in available_names or "crm_create_lead" in available_names:
                t_name = "create_lead" if "create_lead" in available_names else "crm_create_lead"
                calls.append(
                    ToolCall(
                        tool_name=t_name,
                        arguments={
                            "company_name": "مؤسسة النور والتقنية",
                            "contact_name": "المهندس عمر",
                            "email": "omar@al-nour.sa",
                            "phone": "+966500112233",
                            "interest_domain": "Cloud Solutions",
                        },
                    )
                )

        # Ticket / Support
        elif any(w in text for w in ["تذكرة", "مشكلة", "شكوى", "عطل", "تأخير"]):
            if "get_ticket" in available_names or "support_get_ticket" in available_names:
                t_name = "get_ticket" if "get_ticket" in available_names else "support_get_ticket"
                # Extract ticket ID if present (e.g., TIK-8821)
                match = re.search(r"TIK-\d+", text)
                ticket_id = match.group(0) if match else "TIK-9001"
                calls.append(ToolCall(tool_name=t_name, arguments={"ticket_id": ticket_id}))

        return calls

    def _generate_culturally_appropriate_response(
        self, user_msg: str, calls: List[ToolCall], context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Compose high-etiquette response fitting Arabic business norms."""
        # Detect dialect flavor
        is_khaleeji = any(w in user_msg for w in ["طال عمرك", "ابشر", "يا طويل العمر", "فالكم طيب", "سم"])
        is_masri = any(w in user_msg for w in ["باشا", "يا فندم", "حضرتك", "عايزين", "دلوقتي"])

        # Check explicit cultural rubric requirements if provided in context
        honor_str = ""
        greet_str = ""
        if context and context.get("cultural_rubric"):
            rubric = context["cultural_rubric"]
            req_honors = getattr(rubric, "required_honorifics", [])
            req_greets = getattr(rubric, "required_greetings", [])
            if req_greets:
                greet_str = f"{req_greets[0]}، "
            if req_honors:
                honor_str = f"{req_honors[0]}، "

        if is_khaleeji:
            prefix = f"{greet_str}{honor_str}أهلاً ومرحباً بك يا طويل العمر، أبشر بالخير وسعد عينك طال عمرك."
            suffix = "تم تدقيق ومباشرة الإجراءات المطلوبة بحسب الأنظمة المعتمدة، وفي خدمتكم دائماً."
        elif is_masri:
            prefix = f"{greet_str}{honor_str}أهلاً بحضرتك يا فندم وصباحك خير إن شاء الله."
            suffix = "أنا تحت أمر حضرتك وقمنا باتخاذ اللازم فوراً لخدمتكم على أكمل وجه."
        else:
            default_greet = greet_str or "السلام عليكم ورحمة الله وبركاته، "
            prefix = f"{default_greet}{honor_str}تحية طيبة لسعادتكم وبعد."
            suffix = "يسرنا إبلاغكم بأنه تم اتخاذ الإجراءات النظامية فوراً بكل سرور وأبشر بالخير، ونحن في خدمتكم دائماً."

        if not calls:
            return f"{prefix} نشكركم على تواصلكم، ونحن جاهزون لمساعدتكم وتقديم أرقى درجات الخدمة."

        return f"{prefix} {suffix}"
