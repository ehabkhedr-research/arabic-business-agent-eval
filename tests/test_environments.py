import pytest
from ar_biz_agent_eval.environments.mock_crm import MockCRM
from ar_biz_agent_eval.environments.mock_erp import MockERP
from ar_biz_agent_eval.environments.mock_billing import MockBilling
from ar_biz_agent_eval.environments.mock_support import MockSupport
from ar_biz_agent_eval.environments.business_suite import BusinessEnvironment


def test_mock_crm():
    crm = MockCRM()
    # 1. Create Lead
    res = crm.create_lead(
        company_name="مؤسسة التقنية المتقدمة",
        contact_name="الأستاذ فهد",
        email="fahad@advanced-tech.sa",
        interest_domain="Cloud ERP",
    )
    assert res.success is True
    lead_id = res.data["lead"]["lead_id"]
    assert lead_id.startswith("LEAD-")

    # 2. Update Stage
    up_res = crm.update_lead_stage(lead_id=lead_id, new_stage="QUALIFIED")
    assert up_res.success is True
    assert crm.leads[lead_id].status == "QUALIFIED"

    # 3. Create Deal
    deal_res = crm.create_deal(
        deal_name="Enterprise Cloud Migration",
        company_name="مؤسسة التقنية المتقدمة",
        value=150000.0,
        currency="SAR",
    )
    assert deal_res.success is True
    assert deal_res.data["deal"]["value"] == 150000.0


def test_mock_erp():
    erp = MockERP()
    # 1. Verify CR
    v_res = erp.verify_vendor_cr("CR-1010203040")
    assert v_res.success is True
    assert v_res.data["status"] == "ACTIVE"
    assert v_res.data["verified"] is True

    # 2. Check & Reserve Inventory
    inv_res = erp.check_inventory("SKU-SRV-900")
    assert inv_res.success is True
    assert inv_res.data["available_quantity"] >= 15

    res_res = erp.reserve_stock("SKU-SRV-900", quantity=5, reservation_reference="PO-TEST-1")
    assert res_res.success is True
    assert erp.inventory_stock["SKU-SRV-900"] == inv_res.data["available_quantity"] - 5

    # 3. Create PO
    po_res = erp.create_purchase_order(
        vendor_cr="CR-1010203040",
        vendor_name="شركة الرياض للتجهيزات السحابية",
        items=[{"item_name": "سيرفرات ديل باور إيدج", "quantity": 5, "unit_price": 30000.0}],
        payment_terms="Net-30",
    )
    assert po_res.success is True
    po_id = po_res.data["purchase_order"]["po_id"]
    assert po_id in erp.purchase_orders
    assert erp.purchase_orders[po_id]["total_amount"] == 150000.0


def test_mock_billing_zatca_and_vat():
    billing = MockBilling()
    # 1. VAT Calculation
    vat_res = billing.calculate_vat(10000.0, vat_rate=0.15)
    assert vat_res.success is True
    assert vat_res.data["net_amount"] == 10000.0
    assert vat_res.data["vat_amount"] == 1500.0
    assert vat_res.data["gross_amount"] == 11500.0

    # 2. Validate KSA 15-digit VAT
    valid_res = billing.validate_vat_number("300000000000003")
    assert valid_res.success is True
    assert valid_res.data["is_valid"] is True

    invalid_res = billing.validate_vat_number("12345")
    assert invalid_res.data["is_valid"] is False

    # 3. ZATCA Tax Invoice Generation
    inv_res = billing.generate_tax_invoice(
        customer_name="مؤسسة النماء الرقمية",
        customer_vat_number="300000000000003",
        items=[{"name": "استشارات حوسبة سحابية", "quantity": 2, "unit_price": 25000.0}],
        currency="SAR",
    )
    assert inv_res.success is True
    invoice = inv_res.data["invoice"]
    assert invoice["zatca_compliance"]["compliant"] is True
    assert "tlv_qr_base64" in invoice["zatca_compliance"]
    assert invoice["gross_amount"] == 57500.0  # 50000 + 15% VAT (7500)

    # 4. SADAD Bill
    sadad_res = billing.check_sadad_bill("SADAD-1010")
    assert sadad_res.success is True
    assert sadad_res.data["amount_due"] == 11500.0

    # 5. Currency Exchange
    ex_res = billing.get_exchange_rate("USD", "SAR")
    assert ex_res.success is True
    assert ex_res.data["exchange_rate"] == 3.75


def test_mock_support():
    support = MockSupport()
    # 1. Ticket inspection
    t_res = support.get_ticket("TIK-8821")
    assert t_res.success is True
    assert t_res.data["ticket"]["ticket_id"] == "TIK-8821"

    # 2. Escalate
    esc_res = support.escalate_ticket("TIK-8821", "TIER_3_SENIOR", "تأخر غير مبرر للعميل")
    assert esc_res.success is True
    assert support.tickets["TIK-8821"]["status"] == "ESCALATED"

    # 3. Face saving credit
    fsc_res = support.issue_face_saving_credit("TIK-8821", 500.0, "تطييب خاطر للعميل")
    assert fsc_res.success is True
    assert fsc_res.data["credit_record"]["credit_amount"] == 500.0

    # 4. Refund
    ref_res = support.process_customer_refund("TIK-8821", 1000.0, "تعويض عن تعطل")
    assert ref_res.success is True
    assert len(support.refunds) == 1


def test_business_suite_unified_environment():
    suite = BusinessEnvironment()
    tools = suite.get_tools()
    assert len(tools) > 15

    tool_names = {t.name for t in tools}
    assert "create_lead" in tool_names
    assert "verify_vendor_cr" in tool_names
    assert "generate_tax_invoice" in tool_names
    assert "escalate_ticket" in tool_names

    # Direct execution through unified dispatcher
    exec_res = suite.execute_tool("calculate_vat", {"amount": 20000.0, "vat_rate": 0.15})
    assert exec_res.success is True
    assert exec_res.data["gross_amount"] == 23000.0


def test_environments_error_and_edge_cases():
    """Verify error conditions and edge cases across CRM, ERP, Billing, and Support."""
    # 1. ERP Insufficient Inventory
    erp = MockERP()
    inv_check = erp.check_inventory("NON-EXISTENT-SKU")
    assert inv_check.success is False or inv_check.data.get("available_qty", 0) == 0

    res_fail = erp.reserve_stock("SKU-SRV-900", quantity=99999)
    assert res_fail.success is False
    assert "Insufficient" in res_fail.error

    # 2. Billing Invalid VAT Numbers
    billing = MockBilling()
    # KSA VAT must be 15 digits starting and ending with 3
    bad_vat_1 = billing.validate_vat_number("123456789012345", country_code="SA")
    assert bad_vat_1.data["is_valid"] is False

    bad_vat_short = billing.validate_vat_number("3003", country_code="SA")
    assert bad_vat_short.data["is_valid"] is False

    # 3. Support Missing Ticket
    support = MockSupport()
    bad_ticket = support.get_ticket("TIK-NONEXISTENT-999")
    assert bad_ticket.success is False

    # 4. CRM Stage Update Non-Existent Lead
    crm = MockCRM()
    bad_lead_update = crm.update_lead_stage("LEAD-NONEXISTENT", "CLOSED_WON")
    assert bad_lead_update.success is False
