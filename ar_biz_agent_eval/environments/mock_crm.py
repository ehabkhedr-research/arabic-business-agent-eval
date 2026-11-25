"""Mock CRM Environment for MENA B2B Sales workflows."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional
from ar_biz_agent_eval.environments.base import (
    BaseEnvironment,
    ResultDict,
    ToolDefinition,
    ToolParameter,
)


class MockCRMEnvironment(BaseEnvironment):
    """In-memory mock CRM tracking leads, accounts, deals, and sales activities."""

    def _setup_tools(self) -> None:
        if not self.state:
            self.state = {
                "leads": {
                    "LEAD-001": {
                        "id": "LEAD-001",
                        "lead_id": "LEAD-001",
                        "contact_name": "سلطان العتيبي",
                        "company_name": "مجموعة الأفق القابضة",
                        "email": "sultan@alofuq.sa",
                        "phone": "+966501234567",
                        "country": "SA",
                        "status": "QUALIFIED",
                        "stage": "QUALIFIED",
                        "notes": "مهتم بحلول الحوسبة السحابية والبنية التحتية لمراكز البيانات بالرياض",
                        "city": "الرياض",
                    },
                    "LEAD-002": {
                        "id": "LEAD-002",
                        "lead_id": "LEAD-002",
                        "contact_name": "م. طارق فهمي",
                        "company_name": "القاهرة لحلول البرمجيات",
                        "email": "tarek@cairosoft.eg",
                        "phone": "+201012345678",
                        "country": "EG",
                        "status": "NEW",
                        "stage": "NEW",
                        "notes": "يطلب عروض أسعار لتوريد سيرفرات وتراخيص سنوية",
                        "city": "القاهرة",
                    },
                    "LEAD-003": {
                        "id": "LEAD-003",
                        "lead_id": "LEAD-003",
                        "contact_name": "عبدالله الشامسي",
                        "company_name": "دبي للمشاريع الرقمية",
                        "email": "ashamsi@dubai-dp.ae",
                        "phone": "+971509876543",
                        "country": "AE",
                        "status": "QUALIFIED",
                        "stage": "QUALIFIED",
                        "notes": "مشروع تحول رقمي متكامل لقطاع التجزئة بدبي",
                        "city": "دبي",
                    },
                },
                "deals": {
                    "DEAL-101": {
                        "id": "DEAL-101",
                        "deal_id": "DEAL-101",
                        "deal_name": "تطوير البنية السحابية لمجموعة الفطيم",
                        "title": "تطوير البنية السحابية لمجموعة الفطيم",
                        "company_name": "مجموعة الفطيم",
                        "lead_id": "LEAD-003",
                        "amount": 450000.0,
                        "value": 450000.0,
                        "currency": "AED",
                        "stage": "PROPOSAL_SENT",
                        "expected_close_date": "2026-12-31",
                    },
                    "DEAL-102": {
                        "id": "DEAL-102",
                        "deal_id": "DEAL-102",
                        "deal_name": "تجهيز شبكات مركز بيانات أرامكو",
                        "title": "تجهيز شبكات مركز بيانات أرامكو",
                        "company_name": "شركة أرامكو السعودية",
                        "lead_id": "LEAD-001",
                        "amount": 1200000.0,
                        "value": 1200000.0,
                        "currency": "SAR",
                        "stage": "NEGOTIATION",
                        "expected_close_date": "2026-11-30",
                    },
                },
                "activities": [],
            }

        # Canonical Tool: search_leads
        search_def = ToolDefinition(
            name="search_leads",
            description="Search CRM leads by company, contact name, or email.",
            parameters=[
                ToolParameter(name="query", type="string", description="Search query string (name or company)", required=True),
                ToolParameter(name="status", type="string", description="Filter by status (NEW, QUALIFIED, CONTACTED)", required=False),
            ],
        )
        self.register_tool(search_def, self.search_leads)
        self.register_tool(ToolDefinition(name="crm_search_leads", description=search_def.description, parameters=search_def.parameters), self.search_leads)

        # Canonical Tool: create_lead
        create_lead_def = ToolDefinition(
            name="create_lead",
            description="Create a new enterprise sales lead in CRM system.",
            parameters=[
                ToolParameter(name="company_name", type="string", description="Company or organisation name", required=True),
                ToolParameter(name="contact_name", type="string", description="Full contact person name", required=True),
                ToolParameter(name="email", type="string", description="Work email address", required=True),
                ToolParameter(name="phone", type="string", description="Phone number with country code", required=False, default=""),
                ToolParameter(name="country", type="string", description="Country code (SA, AE, EG, etc.)", required=False, default="SA"),
                ToolParameter(name="source", type="string", description="Lead source", required=False, default="inbound"),
                ToolParameter(name="notes", type="string", description="Sales notes and context", required=False, default=""),
            ],
        )
        self.register_tool(create_lead_def, self.create_lead)
        self.register_tool(ToolDefinition(name="crm_create_lead", description=create_lead_def.description, parameters=create_lead_def.parameters), self.create_lead)

        # Canonical Tool: update_lead_stage
        update_lead_def = ToolDefinition(
            name="update_lead_stage",
            description="Update CRM pipeline stage (NEW, QUALIFIED, PROPOSAL_SENT, NEGOTIATION, CLOSED_WON, CLOSED_LOST).",
            parameters=[
                ToolParameter(name="lead_id", type="string", description="Lead identifier (e.g. LEAD-001)", required=True),
                ToolParameter(name="stage", type="string", description="Target stage: NEW, QUALIFIED, PROPOSAL_SENT, NEGOTIATION, CLOSED_WON, CLOSED_LOST", required=True),
            ],
        )
        self.register_tool(update_lead_def, self.update_lead_stage)
        self.register_tool(ToolDefinition(name="crm_update_lead_status", description=update_lead_def.description, parameters=update_lead_def.parameters), self.update_lead_stage)

        # Canonical Tool: create_deal
        create_deal_def = ToolDefinition(
            name="create_deal",
            description="Create a new sales deal / opportunity.",
            parameters=[
                ToolParameter(name="deal_name", type="string", description="Deal title or subject", required=True),
                ToolParameter(name="lead_id", type="string", description="Associated lead ID", required=False, default=""),
                ToolParameter(name="amount", type="number", description="Monetary deal value", required=False),
                ToolParameter(name="value", type="number", description="Monetary deal value alias", required=False),
                ToolParameter(name="currency", type="string", description="Currency code (SAR, AED, EGP, USD)", required=False, default="SAR"),
                ToolParameter(name="expected_close_date", type="string", description="Target closing date YYYY-MM-DD", required=False, default="2026-12-31"),
                ToolParameter(name="stage", type="string", description="Pipeline stage", required=False, default="QUALIFIED"),
            ],
        )
        self.register_tool(create_deal_def, self.create_deal)
        self.register_tool(ToolDefinition(name="crm_create_deal", description=create_deal_def.description, parameters=create_deal_def.parameters), self.create_deal)

        # Canonical Tool: log_sales_activity
        log_act_def = ToolDefinition(
            name="log_sales_activity",
            description="Log a sales meeting, call, or email note on a deal or lead.",
            parameters=[
                ToolParameter(name="deal_id", type="string", description="Target deal or lead ID", required=True),
                ToolParameter(name="activity_type", type="string", description="'CALL', 'MEETING', 'NOTE'", required=True),
                ToolParameter(name="notes_arabic", type="string", description="Summary of activity in Arabic or English", required=True),
            ],
        )
        self.register_tool(log_act_def, self.log_sales_activity)
        self.register_tool(ToolDefinition(name="crm_log_activity", description=log_act_def.description, parameters=log_act_def.parameters), self.log_sales_activity)

    @property
    def leads(self) -> Dict[str, ResultDict]:
        return {k: ResultDict(v) for k, v in self.state.setdefault("leads", {}).items()}

    @property
    def deals(self) -> Dict[str, ResultDict]:
        return {k: ResultDict(v) for k, v in self.state.setdefault("deals", {}).items()}

    def search_leads(self, query: str, status: Optional[str] = None, **kwargs: Any) -> ResultDict:
        query_norm = query.strip().lower()
        matches = []
        for lead in self.state["leads"].values():
            contact = lead.get("contact_name") or lead.get("name", "")
            company = lead.get("company_name") or lead.get("company", "")
            email = lead.get("email", "")
            city = lead.get("city", "")

            match = (
                query_norm in contact.lower()
                or query_norm in company.lower()
                or query_norm in email.lower()
                or query_norm in city.lower()
            )
            if match:
                st = lead.get("status") or lead.get("stage")
                if status and st and st.upper() != status.upper():
                    continue
                matches.append(ResultDict(lead))
        return ResultDict({"success": True, "matches": matches, "count": len(matches)})

    def create_lead(
        self,
        company_name: Optional[str] = None,
        contact_name: Optional[str] = None,
        email: str = "",
        phone: str = "",
        country: str = "SA",
        source: Optional[str] = "inbound",
        notes: str = "",
        name: Optional[str] = None,
        company: Optional[str] = None,
        interest_domain: Optional[str] = None,
        **kwargs: Any,
    ) -> ResultDict:
        actual_name = contact_name or name or "Unknown Contact"
        actual_company = company_name or company or "Unknown Company"
        lead_id = f"LEAD-{uuid.uuid4().hex[:6].upper()}"
        lead = ResultDict({
            "id": lead_id,
            "lead_id": lead_id,
            "contact_name": actual_name,
            "name": actual_name,
            "company_name": actual_company,
            "company": actual_company,
            "email": email,
            "phone": phone,
            "country": country.upper(),
            "status": "QUALIFIED",
            "stage": "QUALIFIED",
            "source": source or "inbound",
            "notes": notes,
            "interest_domain": interest_domain or "",
        })
        self.state["leads"][lead_id] = lead
        return ResultDict({"success": True, "lead_id": lead_id, "status": "QUALIFIED", "lead": lead})

    def update_lead_stage(
        self,
        lead_id: str,
        stage: Optional[str] = None,
        new_stage: Optional[str] = None,
        status: Optional[str] = None,
        **kwargs: Any,
    ) -> ResultDict:
        target_stage = new_stage or stage or status or "QUALIFIED"
        if lead_id not in self.state["leads"]:
            return ResultDict({"success": False, "error": f"Lead {lead_id} not found"})
        prev = self.state["leads"][lead_id].get("stage", "NEW")
        self.state["leads"][lead_id]["stage"] = target_stage.upper()
        self.state["leads"][lead_id]["status"] = target_stage.upper()
        return ResultDict({
            "success": True,
            "lead_id": lead_id,
            "previous_stage": prev,
            "current_stage": target_stage.upper(),
            "status": target_stage.upper(),
        })

    def create_deal(
        self,
        deal_name: Optional[str] = None,
        lead_id: str = "",
        amount: Optional[float] = None,
        currency: str = "SAR",
        expected_close_date: Optional[str] = "2026-12-31",
        stage: str = "QUALIFIED",
        title: Optional[str] = None,
        company: Optional[str] = None,
        value: Optional[float] = None,
        company_name: Optional[str] = None,
        **kwargs: Any,
    ) -> ResultDict:
        actual_title = deal_name or title or "New Enterprise Deal"
        actual_amount = float(amount if amount is not None else (value if value is not None else 0.0))
        actual_company = company_name or company or self.state["leads"].get(lead_id, {}).get("company_name", "")
        deal_id = f"DEAL-{uuid.uuid4().hex[:6].upper()}"
        deal = ResultDict({
            "id": deal_id,
            "deal_id": deal_id,
            "deal_name": actual_title,
            "title": actual_title,
            "lead_id": lead_id,
            "company_name": actual_company,
            "amount": actual_amount,
            "value": actual_amount,
            "currency": currency.upper(),
            "stage": stage.upper(),
            "expected_close_date": expected_close_date,
        })
        self.state["deals"][deal_id] = deal
        return ResultDict({
            "success": True,
            "deal_id": deal_id,
            "deal": deal,
            "deal_name": actual_title,
            "amount": actual_amount,
            "value": actual_amount,
            "currency": currency.upper(),
        })

    def log_sales_activity(
        self,
        deal_id: Optional[str] = None,
        activity_type: str = "NOTE",
        notes_arabic: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        note: Optional[str] = None,
        **kwargs: Any,
    ) -> ResultDict:
        target_id = deal_id or entity_id or "GENERAL"
        content = notes_arabic or note or ""
        activity_id = f"ACT-{uuid.uuid4().hex[:6].upper()}"
        entry = ResultDict({
            "activity_id": activity_id,
            "deal_id": target_id,
            "activity_type": activity_type.upper(),
            "notes_arabic": content,
            "logged_at": "2026-11-25 10:00:00",
        })
        self.state["activities"].append(entry)
        return ResultDict({"success": True, "activity_id": activity_id, "logged_at": entry["logged_at"]})


# Class Alias
MockCRM = MockCRMEnvironment
