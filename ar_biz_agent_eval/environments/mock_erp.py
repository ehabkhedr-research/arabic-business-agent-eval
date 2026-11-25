"""Mock ERP Environment for MENA Procurement, Inventory & Supply Chain."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional
from ar_biz_agent_eval.environments.base import (
    BaseEnvironment,
    ResultDict,
    ToolDefinition,
    ToolParameter,
)


class MockERPEnvironment(BaseEnvironment):
    """In-memory mock ERP system tracking stock, warehouses, certified vendors, and POs."""

    def _setup_tools(self) -> None:
        if not self.state:
            self.state = {
                "warehouses": {
                    "WH-RUH-01": {"id": "WH-RUH-01", "name": "مستودع الرياض المركزي - السلي", "city": "الرياض", "country": "SA"},
                    "WH-DXB-01": {"id": "WH-DXB-01", "name": "مستودع دبي الجنوبي - جبل علي JAFZA", "city": "دبي", "country": "AE"},
                    "WH-CAI-01": {"id": "WH-CAI-01", "name": "مجمع العاشر من رمضان اللوجستي", "city": "القاهرة", "country": "EG"},
                },
                "inventory": {
                    "SKU-SRV-900": {
                        "sku": "SKU-SRV-900",
                        "name": "خادم مؤسسي عالي الأداء Enterprise Server RX-900",
                        "category": "servers",
                        "available_qty": 45,
                        "reserved_qty": 0,
                        "unit_price": 30000.0,
                        "currency": "SAR",
                        "warehouse_id": "WH-RUH-01",
                    },
                    "SRV-A100-8X": {
                        "sku": "SRV-A100-8X",
                        "name": "خوادم سحابية طراز A100 ثمانية المعالجات",
                        "category": "servers",
                        "available_qty": 12,
                        "reserved_qty": 0,
                        "unit_price": 45000.0,
                        "currency": "SAR",
                        "warehouse_id": "WH-RUH-01",
                    },
                    "SKU-SRV-01": {
                        "sku": "SKU-SRV-01",
                        "name": "خادم مؤسسي عالي الأداء Enterprise Server RX-900",
                        "category": "servers",
                        "available_qty": 45,
                        "reserved_qty": 0,
                        "unit_price": 18500.0,
                        "currency": "SAR",
                        "warehouse_id": "WH-RUH-01",
                    },
                    "SKU-SW-02": {
                        "sku": "SKU-SW-02",
                        "name": "موزع شبكة ألياف ضوئية 48 منفذ 10GbE Switch",
                        "category": "networking",
                        "available_qty": 120,
                        "reserved_qty": 5,
                        "unit_price": 4200.0,
                        "currency": "SAR",
                        "warehouse_id": "WH-RUH-01",
                    },
                    "SKU-IOT-03": {
                        "sku": "SKU-IOT-03",
                        "name": "حساسات إنترنت الأشياء الصناعية Industrial IoT Sensor",
                        "category": "iot",
                        "available_qty": 850,
                        "reserved_qty": 50,
                        "unit_price": 350.0,
                        "currency": "SAR",
                        "warehouse_id": "WH-DXB-01",
                    },
                    "SKU-CBL-04": {
                        "sku": "SKU-CBL-04",
                        "name": "كابلات ألياف ضوئية مدرعة Armored Fiber Cables 100m",
                        "category": "cabling",
                        "available_qty": 500,
                        "reserved_qty": 20,
                        "unit_price": 280.0,
                        "currency": "SAR",
                        "warehouse_id": "WH-CAI-01",
                    },
                },
                "suppliers": {
                    "SUP-SA-01": {
                        "id": "SUP-SA-01",
                        "name": "شركة التقنية المتقدمة للتجارة",
                        "cr_number": "1010884920",
                        "unified_700": "7001893421",
                        "country": "SA",
                        "category": "hardware",
                        "status": "certified",
                        "nitaqat_tier": "PLATINUM",
                        "is_vat_registered": True,
                    },
                    "SUP-AE-02": {
                        "id": "SUP-AE-02",
                        "name": "شركة الخليج للحلول الرقمية ذ.م.م",
                        "cr_number": "CN-2049182",
                        "country": "AE",
                        "category": "networking",
                        "status": "certified",
                        "nitaqat_tier": "PLATINUM",
                        "is_vat_registered": True,
                    },
                    "SUP-EG-03": {
                        "id": "SUP-EG-03",
                        "name": "المصرية لتوريدات تكنولوجيا المعلومات",
                        "cr_number": "109842",
                        "country": "EG",
                        "category": "cabling",
                        "status": "certified",
                        "nitaqat_tier": "PLATINUM",
                        "is_vat_registered": True,
                    },
                },
                "reservations": {},
                "purchase_orders": [],
            }

        # Canonical Tool: check_inventory
        chk_inv_def = ToolDefinition(
            name="check_inventory",
            description="Query stock level across regional warehouses for a given SKU.",
            parameters=[
                ToolParameter(name="sku", type="string", description="SKU code (e.g. SRV-A100-8X, SKU-SRV-01, SKU-SRV-900)", required=True),
                ToolParameter(name="warehouse_location", type="string", description="Optional warehouse filter (Riyadh, Dubai, Cairo)", required=False),
            ],
        )
        self.register_tool(chk_inv_def, self.check_inventory)
        self.register_tool(ToolDefinition(name="erp_check_inventory", description=chk_inv_def.description, parameters=chk_inv_def.parameters), self.check_inventory)

        # Canonical Tool: reserve_stock
        res_stock_def = ToolDefinition(
            name="reserve_stock",
            description="Reserve inventory quantity for a customer order.",
            parameters=[
                ToolParameter(name="sku", type="string", description="SKU code to reserve", required=True),
                ToolParameter(name="quantity", type="integer", description="Quantity to reserve", required=True),
                ToolParameter(name="customer_id", type="string", description="Customer or company identifier", required=False, default=""),
                ToolParameter(name="reservation_reference", type="string", description="Reservation reference", required=False, default=""),
            ],
        )
        self.register_tool(res_stock_def, self.reserve_stock)

        # Canonical Tool: verify_vendor_cr
        ver_cr_def = ToolDefinition(
            name="verify_vendor_cr",
            description="Verify Commercial Registration (السجل التجاري) and regional compliance status.",
            parameters=[
                ToolParameter(name="cr_number", type="string", description="10-digit Commercial Registration number", required=True),
                ToolParameter(name="country_code", type="string", description="Country code (SA, AE, EG)", required=False, default="SA"),
            ],
        )
        self.register_tool(ver_cr_def, self.verify_vendor_cr)
        self.register_tool(ToolDefinition(name="erp_verify_vendor_cr", description=ver_cr_def.description, parameters=ver_cr_def.parameters), self.verify_vendor_cr)

        # Canonical Tool: get_supplier_catalog
        cat_def = ToolDefinition(
            name="get_supplier_catalog",
            description="Fetch supplier wholesale catalog, MOQ, and lead days.",
            parameters=[
                ToolParameter(name="category", type="string", description="Product category (hardware, networking, cabling)", required=True),
                ToolParameter(name="supplier_id", type="string", description="Optional supplier ID filter", required=False),
            ],
        )
        self.register_tool(cat_def, self.get_supplier_catalog)
        self.register_tool(ToolDefinition(name="erp_search_suppliers", description=cat_def.description, parameters=cat_def.parameters), self.get_supplier_catalog)

        # Canonical Tool: create_purchase_order
        create_po_def = ToolDefinition(
            name="create_purchase_order",
            description="Create an enterprise purchase order (أمر شراء معتمد).",
            parameters=[
                ToolParameter(name="supplier_id", type="string", description="Certified supplier ID", required=False, default=""),
                ToolParameter(name="vendor_cr", type="string", description="Vendor CR number", required=False, default=""),
                ToolParameter(name="vendor_name", type="string", description="Vendor company name", required=False, default=""),
                ToolParameter(name="items", type="array", description="List of items with sku/item_name, quantity, unit_price", required=True),
                ToolParameter(name="payment_terms", type="string", description="Payment terms (NET_30, NET_60, IMMEDIATE)", required=False, default="NET_30"),
                ToolParameter(name="delivery_date", type="string", description="Target delivery date YYYY-MM-DD", required=False, default="2026-12-15"),
            ],
        )
        self.register_tool(create_po_def, self.create_purchase_order)
        self.register_tool(ToolDefinition(name="erp_generate_purchase_order", description=create_po_def.description, parameters=create_po_def.parameters), self.create_purchase_order)

    @property
    def purchase_orders(self) -> Dict[str, Any]:
        if isinstance(self.state.get("purchase_orders"), list):
            res = {}
            for p in self.state["purchase_orders"]:
                p_id = p.get("po_id") or p.get("po_number")
                if p_id:
                    res[p_id] = ResultDict(p)
            return res
        return {k: ResultDict(v) for k, v in self.state.get("purchase_orders", {}).items()}

    @property
    def inventory_stock(self) -> Dict[str, int]:
        return {k: v.get("available_qty", 0) for k, v in self.state.setdefault("inventory", {}).items()}

    @property
    def inventory_reservations(self) -> Dict[str, Any]:
        return self.state.setdefault("reservations", {})

    def check_inventory(self, sku: str, warehouse_location: Optional[str] = None, **kwargs: Any) -> ResultDict:
        item = self.state["inventory"].get(sku)
        if not item:
            for k, v in self.state["inventory"].items():
                if sku.lower() in k.lower() or sku.lower() in v["name"].lower():
                    item = v
                    break
        if not item:
            return ResultDict({
                "success": False,
                "sku": sku,
                "name": "Unknown",
                "available_qty": 0,
                "available_quantity": 0,
                "reserved_qty": 0,
                "unit_price": 0.0,
                "currency": "SAR",
                "error": f"Item {sku} not found",
            })

        return ResultDict({
            "success": True,
            "sku": item["sku"],
            "name": item["name"],
            "available_qty": item["available_qty"],
            "available_quantity": item["available_qty"],
            "reserved_qty": item.get("reserved_qty", 0),
            "unit_price": item["unit_price"],
            "currency": item["currency"],
        })

    def reserve_stock(
        self,
        sku: str,
        quantity: int,
        customer_id: Optional[str] = None,
        reservation_reference: Optional[str] = None,
        **kwargs: Any,
    ) -> ResultDict:
        item = self.state["inventory"].get(sku)
        if not item:
            for k, v in self.state["inventory"].items():
                if sku.lower() in k.lower():
                    item = v
                    sku = k
                    break

        if not item:
            return ResultDict({"success": False, "error": f"Item {sku} not found"})
        if item["available_qty"] < quantity:
            return ResultDict({
                "success": False,
                "error": f"Insufficient stock. Available: {item['available_qty']}, requested: {quantity}",
            })

        item["available_qty"] -= quantity
        item["reserved_qty"] = item.get("reserved_qty", 0) + quantity
        res_id = f"RES-{uuid.uuid4().hex[:6].upper()}"
        cid = customer_id or reservation_reference or "CUST-DEFAULT"
        res = ResultDict({
            "success": True,
            "reservation_id": res_id,
            "sku": sku,
            "reserved_quantity": quantity,
            "customer_id": cid,
            "status": "CONFIRMED",
        })
        self.state["reservations"][res_id] = res
        return res

    def verify_vendor_cr(self, cr_number: str, country_code: str = "SA", **kwargs: Any) -> ResultDict:
        cr_clean = str(cr_number).strip().replace(" ", "")
        for sup in self.state["suppliers"].values():
            if sup["cr_number"] == cr_clean:
                return ResultDict({
                    "success": True,
                    "verified": True,
                    "cr_number": cr_clean,
                    "legal_name": sup["name"],
                    "status": "ACTIVE",
                    "is_vat_registered": sup.get("is_vat_registered", True),
                    "nitaqat_tier": sup.get("nitaqat_tier", "PLATINUM"),
                })

        # Match CR format like CR-1010203040 or 10 digits
        if cr_clean.startswith("CR-") or (len(cr_clean) >= 9 and cr_clean.replace("CR-", "").isdigit()):
            return ResultDict({
                "success": True,
                "verified": True,
                "cr_number": cr_clean,
                "legal_name": "شركة تجارية معتمدة بالسجل التجاري السعودي",
                "status": "ACTIVE",
                "is_vat_registered": True,
                "nitaqat_tier": "PLATINUM",
            })

        if len(cr_clean) == 10 and cr_clean.isdigit():
            return ResultDict({
                "success": True,
                "verified": True,
                "cr_number": cr_clean,
                "legal_name": "شركة تجارية معتمدة بالسجل التجاري السعودي",
                "status": "ACTIVE",
                "is_vat_registered": True,
                "nitaqat_tier": "PLATINUM",
            })

        return ResultDict({
            "success": False,
            "verified": False,
            "cr_number": cr_clean,
            "legal_name": "غير مسجل",
            "status": "INVALID",
            "is_vat_registered": False,
            "error_message": "Commercial registration number not found or invalid format",
        })

    def get_supplier_catalog(self, category: str, supplier_id: Optional[str] = None, **kwargs: Any) -> ResultDict:
        products = []
        for it in self.state["inventory"].values():
            if it["category"].lower() == category.lower() or category.lower() in ("all", "any"):
                products.append({
                    "sku": it["sku"],
                    "name": it["name"],
                    "unit_price": it["unit_price"],
                    "currency": it["currency"],
                })
        return ResultDict({
            "success": True,
            "products": products,
            "moq": 5,
            "delivery_lead_days": 3,
        })

    def create_purchase_order(
        self,
        supplier_id: Optional[str] = None,
        items: Optional[List[Dict[str, Any]]] = None,
        payment_terms: str = "NET_30",
        delivery_date: str = "2026-12-15",
        vendor_cr: Optional[str] = None,
        vendor_name: Optional[str] = None,
        **kwargs: Any,
    ) -> ResultDict:
        po_number = f"PO-{uuid.uuid4().hex[:6].upper()}"
        actual_items = items or []
        total_val = 0.0
        for it in actual_items:
            q = int(it.get("quantity", 1))
            p = float(it.get("unit_price", 0.0))
            total_val += q * p

        total_amount = round(total_val, 2)
        sup_id = supplier_id or vendor_cr or "SUP-DEFAULT"
        v_name = vendor_name or "المورد المعتمد"

        po = ResultDict({
            "po_id": po_number,
            "po_number": po_number,
            "supplier_id": sup_id,
            "vendor_cr": vendor_cr or sup_id,
            "vendor_name": v_name,
            "items": actual_items,
            "total_value": total_amount,
            "total_amount": total_amount,
            "payment_terms": payment_terms,
            "delivery_date": delivery_date,
            "status": "APPROVED",
        })
        if isinstance(self.state.get("purchase_orders"), list):
            self.state["purchase_orders"].append(po)
        else:
            self.state.setdefault("purchase_orders", {})[po_number] = po

        return ResultDict({
            "success": True,
            "purchase_order": po,
            "po_id": po_number,
            "po_number": po_number,
            "total_amount": total_amount,
            "status": "APPROVED",
        })


# Class Alias
MockERP = MockERPEnvironment
