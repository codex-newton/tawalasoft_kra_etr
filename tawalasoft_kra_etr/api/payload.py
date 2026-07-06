import frappe
from frappe.utils import flt, getdate


def build_sales_invoice_payload(doc, price_mode):
    """price_mode: 1 = Inclusive, 2 = Exclusive"""
    seller_pin = frappe.db.get_value("Company", doc.company, "tax_id") or ""
    customer_pin = frappe.db.get_value("Customer", doc.customer, "tax_id") or ""

    rel_doc_number = ""
    if doc.is_return and doc.return_against:
        rel_doc_number = frappe.db.get_value(
            "Sales Invoice", doc.return_against, "custom_cu_invoice_number"
        ) or ""

    return {
        "invoice_date": getdate(doc.posting_date).strftime("%d_%m_%Y"),
        "invoice_number": doc.name,
        "invoice_pin": seller_pin,
        "customer_pin": customer_pin,
        "customer_exid": "",
        "grand_total": f"{flt(abs(doc.grand_total), 2):.2f}",
        "net_subtotal": f"{flt(abs(doc.net_total), 2):.2f}",
        "tax_total": f"{flt(abs(doc.total_taxes_and_charges or 0), 2):.2f}",
        "net_discount_total": f"{flt(abs(doc.discount_amount or 0), 2):.2f}",
        "sel_currency": doc.currency or "KSH",
        "rel_doc_number": rel_doc_number,
        "items_list": _items(doc, price_mode),
    }


def _items(doc, price_mode):
    lines = []
    for item in doc.items:
        desc = _clean(item.item_name or item.item_code)
        qty = flt(abs(item.qty), 2)
        if price_mode == 2:
            unit = flt(abs(item.net_rate or item.rate), 2)
            total = flt(abs(item.net_amount or item.amount), 2)
        else:
            unit = flt(abs(item.rate), 2)
            total = flt(abs(item.amount), 2)
        lines.append(f" {desc} {qty:.2f} {unit:.2f} {total:.2f}"[:512])
    return lines


def _clean(text):
    if not text:
        return ""
    return str(text).replace("\n", " ").replace("\r", " ").replace("\t", " ").replace('"', "").strip()
