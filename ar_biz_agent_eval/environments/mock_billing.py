"""Mock Billing Environment: GCC VAT, ZATCA Phase 2 FATOORA & Multi-Currency."""

from __future__ import annotations

import base64
import hashlib
import time
import uuid
from typing import Any, Dict, List, Optional
from ar_biz_agent_eval.environments.base import (
    BaseEnvironment,
    ResultDict,
    ToolDefinition,
    ToolParameter,
)


class MockBillingEnvironment(BaseEnvironment):
    """Mock Billing & Invoicing Engine adhering to MENA tax and regulatory standards."""

    # Regional Standard VAT Rates
    VAT_RATES: Dict[str, float] = {
        "SA": 0.15,
        "KSA": 0.15,
        "AE": 0.05,
        "UAE": 0.05,
        "EG": 0.14,
        "EGYPT": 0.14,
        "BH": 0.10,
        "BAHRAIN": 0.10,
        "OM": 0.05,
        "OMAN": 0.05,
        "KW": 0.00,
        "KUWAIT": 0.00,
        "QA": 0.00,
        "QATAR": 0.00,
    }

    # Standard FX Rates against USD
    USD_RATES: Dict[str, float] = {
        "USD": 1.0,
        "SAR": 3.75,
        "AED": 3.6725,
        "EGP": 48.50,
        "KWD": 0.308,
        "EUR": 0.92,
        "QAR": 3.64,
        "BHD": 0.376,
        "OMR": 0.385,
    }

    def _setup_tools(self) -> None:
        if not self.state:
            self.state = {
                "invoices": [
                    {
                        "invoice_id": "INV-2026-001",
                        "id": "INV-2026-001",
                        "buyer_name": "شركة الرياض للصناعات المتقدمة",
                        "customer_name": "شركة الرياض للصناعات المتقدمة",
                        "buyer_vat": "300189382100003",
                        "customer_vat_number": "300189382100003",
                        "country": "SA",
                        "currency": "SAR",
                        "subtotal": 100000.0,
                        "tax_rate": 0.15,
                        "vat_rate": 0.15,
                        "vat_amount": 15000.0,
                        "total_amount": 115000.0,
                        "gross_amount": 115000.0,
                        "status": "cleared",
                        "payment_status": "UNPAID",
                        "is_zatca_compliant": True,
                        "csid_hash": "a4f89d3c1b6e4d2a9f7e5c8b1a3d5e7f9a1b3c5d7e9f1a3b5c7d9e1f3a5b7c9d",
                        "qr_payload": "AQ9SaXlhZGggQWR2YW5jZWQTAzMwMDE4OTM4MjEwMDAwMxIGMjAyNi0xMS0yNQ==",
                        "zatca_compliance": {
                            "compliant": True,
                            "csid_hash": "a4f89d3c1b6e4d2a9f7e5c8b1a3d5e7f9a1b3c5d7e9f1a3b5c7d9e1f3a5b7c9d",
                            "tlv_qr_base64": "AQ9SaXlhZGggQWR2YW5jZWQTAzMwMDE4OTM4MjEwMDAwMxIGMjAyNi0xMS0yNQ==",
                        },
                    }
                ],
                "customers": [
                    {
                        "id": "CUST-901",
                        "name": "شركة الأفق المتقدم لتقنية المعلومات",
                        "cr_number": "1010456789",
                        "tax_id": "310123456700003",
                        "balance_due": 0.0,
                    }
                ],
                "credit_notes": [],
                "sadad_bills": {
                    "001-987654": {"biller_code": "001", "bill_number": "987654", "amount_due": 4500.0, "currency": "SAR", "status": "UNPAID"},
                    "002-123456": {"biller_code": "002", "bill_number": "123456", "amount_due": 12500.0, "currency": "SAR", "status": "PAID"},
                    "SADAD-1010": {"biller_code": "SADAD", "bill_number": "SADAD-1010", "amount_due": 11500.0, "currency": "SAR", "status": "UNPAID"},
                },
                "payments": [],
                "last_invoice_hash": "a4f89d3c1b6e4d2a9f7e5c8b1a3d5e7f9a1b3c5d7e9f1a3b5c7d9e1f3a5b7c9d",
            }

        # Canonical Tool: calculate_vat
        calc_vat_def = ToolDefinition(
            name="calculate_vat",
            description="Compute subtotal, VAT amount, and total according to regional tax rules.",
            parameters=[
                ToolParameter(name="amount", type="number", description="Pre-tax or total amount", required=True),
                ToolParameter(name="tax_rate", type="number", description="VAT rate (default 0.15 for KSA, 0.05 for UAE, 0.14 for Egypt)", required=False, default=0.15),
                ToolParameter(name="is_inclusive", type="boolean", description="Whether input amount already includes VAT", required=False, default=False),
            ],
        )
        self.register_tool(calc_vat_def, self.calculate_vat)
        self.register_tool(ToolDefinition(name="billing_calculate_gcc_vat", description=calc_vat_def.description, parameters=calc_vat_def.parameters), self.calculate_vat)

        # Canonical Tool: validate_vat_number
        val_vat_def = ToolDefinition(
            name="validate_vat_number",
            description="Validate 15-digit GCC VAT ID (e.g. starts and ends with 3 in Saudi Arabia).",
            parameters=[
                ToolParameter(name="vat_number", type="string", description="15-digit VAT tax identifier", required=True),
                ToolParameter(name="country_code", type="string", description="Country code (SA, AE)", required=False, default="SA"),
            ],
        )
        self.register_tool(val_vat_def, self.validate_vat_number)

        # Canonical Tool: generate_tax_invoice
        gen_inv_def = ToolDefinition(
            name="generate_tax_invoice",
            description="Generate ZATCA Phase-2 / GCC e-Invoice with QR TLV, invoice hash, and tax totals.",
            parameters=[
                ToolParameter(name="buyer_name", type="string", description="Full buyer enterprise name", required=False),
                ToolParameter(name="customer_name", type="string", description="Customer enterprise name", required=False),
                ToolParameter(name="buyer_vat", type="string", description="Buyer 15-digit Tax ID", required=False),
                ToolParameter(name="customer_vat_number", type="string", description="Customer VAT ID", required=False),
                ToolParameter(name="items", type="array", description="List of items with sku, quantity, unit_price", required=True),
                ToolParameter(name="currency", type="string", description="Currency code (SAR, AED, EGP, USD)", required=False, default="SAR"),
                ToolParameter(name="tax_rate", type="number", description="Tax rate float (e.g. 0.15)", required=False, default=0.15),
                ToolParameter(name="buyer_cr", type="string", description="Optional buyer commercial registration number", required=False),
            ],
        )
        self.register_tool(gen_inv_def, self.generate_tax_invoice)
        self.register_tool(ToolDefinition(name="billing_create_zatca_invoice", description=gen_inv_def.description, parameters=gen_inv_def.parameters), self.generate_tax_invoice)

        # Canonical Tool: issue_credit_note
        cred_def = ToolDefinition(
            name="issue_credit_note",
            description="Issue tax-adjusted credit note for returns or billing corrections.",
            parameters=[
                ToolParameter(name="original_invoice_id", type="string", description="Original invoice ID", required=True),
                ToolParameter(name="reason_arabic", type="string", description="Business justification in Arabic", required=True),
                ToolParameter(name="refund_amount", type="number", description="Amount to credit/refund", required=True),
            ],
        )
        self.register_tool(cred_def, self.issue_credit_note)
        self.register_tool(ToolDefinition(name="billing_apply_credit_note", description=cred_def.description, parameters=cred_def.parameters), self.issue_credit_note)

        # Canonical Tool: check_sadad_bill
        sadad_def = ToolDefinition(
            name="check_sadad_bill",
            description="Query Saudi Sadad bill status.",
            parameters=[
                ToolParameter(name="biller_code", type="string", description="Biller code (e.g. 001, 002)", required=False),
                ToolParameter(name="bill_number", type="string", description="Account or bill number", required=False),
            ],
        )
        self.register_tool(sadad_def, self.check_sadad_bill)

        # Canonical Tool: get_exchange_rate
        fx_def = ToolDefinition(
            name="get_exchange_rate",
            description="Query regional foreign exchange rate between currencies (SAR, AED, EGP, USD, KWD).",
            parameters=[
                ToolParameter(name="from_currency", type="string", description="Base currency code", required=True),
                ToolParameter(name="to_currency", type="string", description="Target currency code", required=True),
            ],
        )
        self.register_tool(fx_def, self.get_exchange_rate)
        self.register_tool(ToolDefinition(name="billing_get_currency_rate", description=fx_def.description, parameters=fx_def.parameters), self.get_exchange_rate)

    @property
    def invoices(self) -> Dict[str, Any]:
        if isinstance(self.state.get("invoices"), list):
            res = {}
            for inv in self.state["invoices"]:
                inv_id = inv.get("invoice_id") or inv.get("id")
                if inv_id:
                    res[inv_id] = ResultDict(inv)
            return res
        return {k: ResultDict(v) for k, v in self.state.get("invoices", {}).items()}

    def calculate_vat(
        self,
        amount: Optional[float] = None,
        tax_rate: Optional[float] = None,
        vat_rate: Optional[float] = None,
        is_inclusive: bool = False,
        subtotal: Optional[float] = None,
        country: Optional[str] = "SA",
        **kwargs: Any,
    ) -> ResultDict:
        base_amt = float(amount if amount is not None else (subtotal if subtotal is not None else 0.0))
        rate = float(
            vat_rate
            if vat_rate is not None
            else (tax_rate if tax_rate is not None else self.VAT_RATES.get((country or "SA").upper(), 0.15))
        )

        if is_inclusive:
            sub = round(base_amt / (1.0 + rate), 2)
            vat_amt = round(base_amt - sub, 2)
            tot = round(base_amt, 2)
        else:
            sub = round(base_amt, 2)
            vat_amt = round(sub * rate, 2)
            tot = round(sub + vat_amt, 2)

        return ResultDict({
            "success": True,
            "subtotal": sub,
            "net_amount": sub,
            "tax_rate": rate,
            "vat_rate": rate,
            "vat_amount": vat_amt,
            "total_amount": tot,
            "gross_amount": tot,
        })

    def validate_vat_number(self, vat_number: str, country_code: str = "SA", **kwargs: Any) -> ResultDict:
        vat_clean = str(vat_number).strip().replace(" ", "")
        c_code = country_code.upper()

        if c_code in ("SA", "KSA"):
            if len(vat_clean) == 15 and vat_clean.isdigit() and vat_clean.startswith("3") and vat_clean.endswith("3"):
                return ResultDict({
                    "success": True,
                    "vat_number": vat_clean,
                    "is_valid": True,
                    "entity_type": "CORPORATE",
                    "error_message": None,
                })
            return ResultDict({
                "success": False,
                "vat_number": vat_clean,
                "is_valid": False,
                "entity_type": "UNKNOWN",
                "error_message": "Saudi Tax ID must be 15 digits starting and ending with 3",
            })

        if len(vat_clean) >= 9:
            return ResultDict({"success": True, "vat_number": vat_clean, "is_valid": True, "entity_type": "CORPORATE", "error_message": None})

        return ResultDict({"success": False, "vat_number": vat_clean, "is_valid": False, "entity_type": "UNKNOWN", "error_message": "Invalid Tax ID length"})

    def generate_tax_invoice(
        self,
        buyer_name: Optional[str] = None,
        buyer_vat: Optional[str] = None,
        items: Optional[List[Dict[str, Any]]] = None,
        currency: str = "SAR",
        tax_rate: Optional[float] = None,
        vat_rate: Optional[float] = None,
        buyer_cr: Optional[str] = None,
        customer_name: Optional[str] = None,
        customer_vat_number: Optional[str] = None,
        customer_vat_id: Optional[str] = None,
        **kwargs: Any,
    ) -> ResultDict:
        b_name = buyer_name or customer_name or "Client Company"
        b_vat = buyer_vat or customer_vat_number or customer_vat_id or "300000000000003"
        actual_items = items or []
        rate = float(tax_rate if tax_rate is not None else (vat_rate if vat_rate is not None else 0.15))

        subtotal = 0.0
        for it in actual_items:
            qty = int(it.get("quantity", 1))
            price = float(it.get("unit_price", 0.0))
            subtotal += qty * price

        subtotal = round(subtotal, 2)
        vat_amount = round(subtotal * rate, 2)
        total_amount = round(subtotal + vat_amount, 2)

        inv_uuid = str(uuid.uuid4())
        invoice_id = f"INV-{time.strftime('%Y%m')}-{uuid.uuid4().hex[:4].upper()}"
        issue_date = time.strftime("%Y-%m-%d")

        hash_input = f"{invoice_id}|{issue_date}|{subtotal}|{vat_amount}|{total_amount}|{b_vat}"
        csid_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()
        qr_bytes = f"Seller|{b_vat}|{issue_date}|{total_amount}|{vat_amount}|{csid_hash[:16]}".encode("utf-8")
        qr_payload = base64.b64encode(qr_bytes).decode("ascii")

        zatca_comp = ResultDict({
            "compliant": True,
            "csid_hash": csid_hash,
            "tlv_qr_base64": qr_payload,
            "phase": 2,
        })

        invoice_record = ResultDict({
            "invoice_id": invoice_id,
            "id": invoice_id,
            "invoice_uuid": inv_uuid,
            "issue_date": issue_date,
            "buyer_name": b_name,
            "customer_name": b_name,
            "buyer_vat": b_vat,
            "customer_vat_number": b_vat,
            "buyer_cr": buyer_cr,
            "items": actual_items,
            "subtotal": subtotal,
            "tax_rate": rate,
            "vat_rate": rate,
            "vat_amount": vat_amount,
            "total_amount": total_amount,
            "gross_amount": total_amount,
            "currency": currency.upper(),
            "qr_payload": qr_payload,
            "csid_hash": csid_hash,
            "is_zatca_compliant": True,
            "zatca_compliance": zatca_comp,
            "status": "cleared",
            "payment_status": "UNPAID",
        })

        if isinstance(self.state.get("invoices"), list):
            self.state["invoices"].append(invoice_record)
        else:
            self.state.setdefault("invoices", {})[invoice_id] = invoice_record

        return ResultDict({
            "success": True,
            "invoice": invoice_record,
            "invoice_id": invoice_id,
            "gross_amount": total_amount,
            "total_amount": total_amount,
        })

    def issue_credit_note(
        self,
        original_invoice_id: Optional[str] = None,
        reason_arabic: Optional[str] = None,
        refund_amount: Optional[float] = None,
        invoice_id: Optional[str] = None,
        amount: Optional[float] = None,
        reason: Optional[str] = None,
        **kwargs: Any,
    ) -> ResultDict:
        inv_id = original_invoice_id or invoice_id or "INV-UNKNOWN"
        justification = reason_arabic or reason or "Credit Adjustment"
        amt = float(refund_amount if refund_amount is not None else (amount if amount is not None else 0.0))
        vat_refunded = round(amt * 0.15 / 1.15, 2)

        cn_id = f"CN-{uuid.uuid4().hex[:6].upper()}"
        cn_record = ResultDict({
            "credit_note_id": cn_id,
            "original_invoice": inv_id,
            "reason_arabic": justification,
            "refund_amount": amt,
            "refunded_vat": vat_refunded,
            "status": "ISSUED",
        })
        if isinstance(self.state.get("credit_notes"), list):
            self.state["credit_notes"].append(cn_record)
        else:
            self.state.setdefault("credit_notes", {})[cn_id] = cn_record

        return ResultDict({"success": True, "credit_note": cn_record, **cn_record})

    def check_sadad_bill(
        self,
        bill_number_or_code: Optional[str] = None,
        bill_number: Optional[str] = None,
        biller_code: Optional[str] = None,
        **kwargs: Any,
    ) -> ResultDict:
        # Support single arg check_sadad_bill("SADAD-1010")
        arg = bill_number_or_code or bill_number or biller_code or ""
        if arg in self.state.get("sadad_bills", {}):
            return ResultDict({"success": True, **self.state["sadad_bills"][arg]})

        key = f"{biller_code or '001'}-{bill_number or arg}"
        bill = self.state.get("sadad_bills", {}).get(key)
        if bill:
            return ResultDict({"success": True, **bill})

        # Match substring or default
        if "1010" in arg or "SADAD" in arg:
            return ResultDict({
                "success": True,
                "biller_code": "SADAD",
                "bill_number": arg,
                "amount_due": 11500.0,
                "currency": "SAR",
                "status": "UNPAID",
            })

        return ResultDict({
            "success": True,
            "biller_code": biller_code or "001",
            "bill_number": bill_number or arg,
            "amount_due": 3500.0,
            "currency": "SAR",
            "status": "UNPAID",
        })

    def get_exchange_rate(
        self,
        from_currency: Optional[str] = None,
        to_currency: Optional[str] = None,
        base_currency: Optional[str] = None,
        target_currency: Optional[str] = None,
        **kwargs: Any,
    ) -> ResultDict:
        f_cur = (from_currency or base_currency or "USD").upper()
        t_cur = (to_currency or target_currency or "SAR").upper()

        f_rate = self.USD_RATES.get(f_cur, 1.0)
        t_rate = self.USD_RATES.get(t_cur, 1.0)
        rate = round((1.0 / f_rate) * t_rate, 4)

        return ResultDict({
            "success": True,
            "from_currency": f_cur,
            "to_currency": t_cur,
            "rate": rate,
            "exchange_rate": rate,
            "timestamp": "2026-11-25 10:00:00",
        })


# Class Alias
MockBilling = MockBillingEnvironment
