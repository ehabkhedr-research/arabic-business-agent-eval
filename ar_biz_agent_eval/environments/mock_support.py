"""Mock Support Desk Environment for MENA Customer Care, SLAs & Escalations."""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional
from ar_biz_agent_eval.environments.base import (
    BaseEnvironment,
    ResultDict,
    ToolDefinition,
    ToolParameter,
)


class MockSupportEnvironment(BaseEnvironment):
    """In-memory mock support desk handling tickets, SLAs, and face-saving resolutions."""

    def _setup_tools(self) -> None:
        if not self.state:
            self.state = {
                "tickets": {
                    "TIK-8821": {
                        "ticket_id": "TIK-8821",
                        "id": "TIK-8821",
                        "customer_name": "مؤسسة الابتكار الرقمي",
                        "customer_tier": "VIP",
                        "issue": "تأخر غير مبرر في التوريد وتفعيل النظام",
                        "priority": "P1",
                        "status": "OPEN",
                        "sla_remaining_minutes": 15,
                        "escalated": False,
                    },
                    "TCK-1001": {
                        "ticket_id": "TCK-1001",
                        "id": "TCK-1001",
                        "customer_name": "شركة البتروكيماويات الحديثة",
                        "customer_tier": "VIP",
                        "issue": "انقطاع مفاجئ في خدمة بوابة الدفع والـ Webhook لا يستجيب",
                        "priority": "P1",
                        "status": "OPEN",
                        "sla_remaining_minutes": 0,
                        "escalated": False,
                    },
                    "TCK-1002": {
                        "ticket_id": "TCK-1002",
                        "id": "TCK-1002",
                        "customer_name": "م. أشرف عبد العزيز",
                        "customer_tier": "STANDARD",
                        "issue": "تأخر شحنة كابلات الألياف الضوئية لأكثر من أسبوعين",
                        "priority": "P2",
                        "status": "PENDING_CUSTOMER",
                        "sla_remaining_minutes": 60,
                        "escalated": False,
                    },
                    "TCK-1003": {
                        "ticket_id": "TCK-1003",
                        "id": "TCK-1003",
                        "customer_name": "سعود القحطاني",
                        "customer_tier": "STANDARD",
                        "issue": "استفسار عن طريقة سداد فاتورة عبر نظام سداد",
                        "priority": "P3",
                        "status": "RESOLVED",
                        "sla_remaining_minutes": 240,
                        "escalated": False,
                    },
                },
                "escalations": [],
                "refunds": [],
                "courtesy_credits": [],
            }

        # Canonical Tool: get_ticket
        get_tck_def = ToolDefinition(
            name="get_ticket",
            description="Fetch customer service ticket and SLA details.",
            parameters=[
                ToolParameter(name="ticket_id", type="string", description="Ticket identifier (e.g. TCK-1001, TIK-8821)", required=True),
            ],
        )
        self.register_tool(get_tck_def, self.get_ticket)
        self.register_tool(ToolDefinition(name="support_get_ticket", description=get_tck_def.description, parameters=get_tck_def.parameters), self.get_ticket)

        # Canonical Tool: update_ticket_status
        upd_tck_def = ToolDefinition(
            name="update_ticket_status",
            description="Update ticket status and resolution notes in Arabic.",
            parameters=[
                ToolParameter(name="ticket_id", type="string", description="Ticket identifier", required=True),
                ToolParameter(name="status", type="string", description="Status (OPEN, PENDING_CUSTOMER, ESCALATED, RESOLVED, CLOSED)", required=True),
                ToolParameter(name="resolution_notes_ar", type="string", description="Resolution notes or reply in Arabic", required=True),
            ],
        )
        self.register_tool(upd_tck_def, self.update_ticket_status)
        self.register_tool(ToolDefinition(name="support_update_ticket", description=upd_tck_def.description, parameters=upd_tck_def.parameters), self.update_ticket_status)

        # Canonical Tool: escalate_ticket
        esc_tck_def = ToolDefinition(
            name="escalate_ticket",
            description="Escalate incident to tier-2 / executive desk.",
            parameters=[
                ToolParameter(name="ticket_id", type="string", description="Ticket identifier", required=True),
                ToolParameter(name="department", type="string", description="Department (OPERATIONS, FINANCE, LEGAL, EXECUTIVE)", required=False, default="OPERATIONS"),
                ToolParameter(name="urgency", type="string", description="Urgency (HIGH, CRITICAL)", required=False, default="CRITICAL"),
                ToolParameter(name="escalation_reason_ar", type="string", description="Escalation reason in Arabic", required=True),
            ],
        )
        self.register_tool(esc_tck_def, self.escalate_ticket)
        self.register_tool(ToolDefinition(name="support_escalate_ticket", description=esc_tck_def.description, parameters=esc_tck_def.parameters), self.escalate_ticket)

        # Canonical Tool: process_customer_refund
        ref_def = ToolDefinition(
            name="process_customer_refund",
            description="Process customer refund with policy verification.",
            parameters=[
                ToolParameter(name="order_id", type="string", description="Order or invoice ID", required=True),
                ToolParameter(name="amount", type="number", description="Refund amount requested", required=True),
                ToolParameter(name="justification_ar", type="string", description="Justification in Arabic", required=True),
            ],
        )
        self.register_tool(ref_def, self.process_customer_refund)

        # Canonical Tool: issue_face_saving_credit
        cred_def = ToolDefinition(
            name="issue_face_saving_credit",
            description="Issue goodwill courtesy discount or credit to preserve commercial relationship and save face.",
            parameters=[
                ToolParameter(name="customer_id", type="string", description="Customer or company ID", required=True),
                ToolParameter(name="credit_amount", type="number", description="Credit amount in SAR", required=True),
                ToolParameter(name="courtesy_reason_ar", type="string", description="Courteous explanation in Arabic honoring relationship", required=True),
            ],
        )
        self.register_tool(cred_def, self.issue_face_saving_credit)
        self.register_tool(ToolDefinition(name="support_issue_face_saving_credit", description=cred_def.description, parameters=cred_def.parameters), self.issue_face_saving_credit)

    @property
    def tickets(self) -> Dict[str, Any]:
        return self.state.setdefault("tickets", {})

    @property
    def refunds(self) -> List[Dict[str, Any]]:
        return self.state.setdefault("refunds", [])

    def get_ticket(self, ticket_id: str, **kwargs: Any) -> ResultDict:
        tck = self.state["tickets"].get(ticket_id)
        if not tck:
            return ResultDict({"success": False, "ticket_id": ticket_id, "error": f"Ticket {ticket_id} not found"})
        data = {
            "ticket_id": tck.get("ticket_id") or tck.get("id"),
            "customer_name": tck.get("customer_name"),
            "customer_tier": tck.get("customer_tier", "STANDARD"),
            "issue": tck.get("issue") or tck.get("subject"),
            "priority": tck.get("priority", "P3"),
            "status": tck.get("status", "OPEN"),
            "sla_remaining_minutes": tck.get("sla_remaining_minutes", 60),
        }
        return ResultDict({"success": True, "ticket": ResultDict(data), **data})

    def update_ticket_status(
        self,
        ticket_id: str,
        status: str,
        resolution_notes_ar: Optional[str] = None,
        internal_note: Optional[str] = None,
        reply_to_customer: Optional[str] = None,
        **kwargs: Any,
    ) -> ResultDict:
        tck = self.state["tickets"].get(ticket_id)
        if not tck:
            return ResultDict({"success": False, "error": f"Ticket {ticket_id} not found"})

        tck["status"] = status.upper()
        note = resolution_notes_ar or internal_note or reply_to_customer or ""
        tck.setdefault("notes", []).append(note)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        return ResultDict({
            "success": True,
            "ticket_id": ticket_id,
            "updated_status": status.upper(),
            "status": status.upper(),
            "timestamp": timestamp,
        })

    def escalate_ticket(
        self,
        ticket_id: str,
        escalation_reason_ar: Optional[str] = None,
        department: Optional[str] = None,
        urgency: Optional[str] = None,
        reason: Optional[str] = None,
        urgency_level: Optional[str] = None,
        *args: Any,
        **kwargs: Any,
    ) -> ResultDict:
        tck = self.state["tickets"].get(ticket_id)
        if not tck:
            return ResultDict({"success": False, "error": f"Ticket {ticket_id} not found"})

        # Positional handling: escalate_ticket("TIK-8821", "TIER_3_SENIOR", "تأخر غير مبرر للعميل")
        dep = department or "OPERATIONS"
        r_text = reason or escalation_reason_ar or "Critical Escalation"
        if args:
            if len(args) == 1:
                r_text = str(args[0])
            elif len(args) >= 2:
                dep = str(args[0])
                r_text = str(args[1])
        elif escalation_reason_ar and department is None and not any(kw in kwargs for kw in ["reason", "department"]):
            # Check if second arg was passed as department or reason
            if escalation_reason_ar.startswith("TIER_") or escalation_reason_ar in ("OPERATIONS", "FINANCE", "LEGAL", "EXECUTIVE"):
                dep = escalation_reason_ar
                r_text = kwargs.get("reason", "Critical Escalation")

        u_val = (urgency_level or urgency or "CRITICAL").upper()
        ref = f"ESC-{uuid.uuid4().hex[:6].upper()}"

        tck["status"] = "ESCALATED"
        tck["escalated"] = True

        entry = ResultDict({
            "ticket_id": ticket_id,
            "escalation_ref": ref,
            "department": dep.upper(),
            "urgency": u_val,
            "reason": r_text,
            "escalated_to": f"{dep.upper()}_LEAD",
        })
        self.state["escalations"].append(entry)

        return ResultDict({
            "success": True,
            "ticket_id": ticket_id,
            "escalated_to": entry["escalated_to"],
            "escalation_ref": ref,
            "status": "ESCALATED",
        })

    def process_customer_refund(
        self,
        order_id: str,
        amount: float,
        justification_ar: Optional[str] = None,
        *args: Any,
        **kwargs: Any,
    ) -> ResultDict:
        ref_id = f"REF-{uuid.uuid4().hex[:6].upper()}"
        amt = float(amount)
        just = justification_ar or (args[0] if args else "Customer Refund Compensation")

        if amt > 5000.0:
            return ResultDict({
                "success": False,
                "refund_id": ref_id,
                "order_id": order_id,
                "amount": amt,
                "status": "REJECTED_EXCEEDS_POLICY",
                "error": "Refunds above 5,000 SAR exceed agent self-service limit and require executive committee approval.",
            })

        entry = ResultDict({
            "refund_id": ref_id,
            "order_id": order_id,
            "ticket_id": order_id,
            "amount": amt,
            "justification_ar": just,
            "status": "PROCESSED",
        })
        self.state["refunds"].append(entry)
        return ResultDict({
            "success": True,
            "refund": entry,
            "refund_id": ref_id,
            "order_id": order_id,
            "amount": amt,
            "status": "PROCESSED",
        })

    def issue_face_saving_credit(
        self,
        customer_id: str,
        credit_amount: Optional[float] = None,
        courtesy_reason_ar: Optional[str] = None,
        customer_name: Optional[str] = None,
        credit_amount_sar: Optional[float] = None,
        goodwill_message: Optional[str] = None,
        *args: Any,
        **kwargs: Any,
    ) -> ResultDict:
        amt = float(credit_amount if credit_amount is not None else (credit_amount_sar if credit_amount_sar is not None else (args[0] if args else 500.0)))
        msg = courtesy_reason_ar or goodwill_message or (args[1] if len(args) > 1 else "تقدير الشراكة الاستراتيجية وحفظ ماء الوجه")
        cid = customer_id or customer_name or "CUST-VALUED"

        code = f"COURTESY-{uuid.uuid4().hex[:4].upper()}"
        credit_entry = ResultDict({
            "credit_id": f"CRED-{uuid.uuid4().hex[:6].upper()}",
            "customer_id": cid,
            "credit_amount": amt,
            "courtesy_code": code,
            "status": "APPLIED",
            "message": msg,
        })
        self.state["courtesy_credits"].append(credit_entry)
        return ResultDict({"success": True, "credit_record": credit_entry, **credit_entry})


# Class Alias
MockSupport = MockSupportEnvironment
