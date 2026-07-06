import frappe
from frappe import _
from frappe.utils import now_datetime

from tawalasoft_kra_etr.api.client import KRAETRClient
from tawalasoft_kra_etr.api.payload import build_sales_invoice_payload


def on_sales_invoice_submit(doc, method=None):
    settings = frappe.get_single("KRA ETR Settings")
    if not settings.enabled or doc.get("custom_etr_signed"):
        return
    try:
        _sign(doc, settings)
    except Exception as e:
        frappe.log_error(title=f"KRA ETR sign failed: {doc.name}", message=frappe.get_traceback())
        doc.db_set("custom_etr_error", str(e)[:500], commit=True)


def block_cancel_if_signed(doc, method=None):
    if doc.get("custom_etr_signed"):
        frappe.throw(_("Sales Invoice {0} is KRA-signed. Issue a credit note.").format(doc.name))


@frappe.whitelist()
def retry_sign(sales_invoice):
    doc = frappe.get_doc("Sales Invoice", sales_invoice)
    if doc.docstatus != 1:
        frappe.throw(_("Invoice must be submitted"))
    if doc.get("custom_etr_signed"):
        frappe.throw(_("Already signed"))
    _sign(doc, frappe.get_single("KRA ETR Settings"))
    return {
        "cu_invoice_number": doc.custom_cu_invoice_number,
        "verify_url": doc.custom_etr_verify_url,
    }


def _sign(doc, settings):
    price_mode = 1 if settings.default_price_mode == "Inclusive" else 2
    slug = "credit-note" if doc.is_return else "invoice"
    payload = build_sales_invoice_payload(doc, price_mode)
    response = KRAETRClient().sign(slug, price_mode, payload)
    doc.db_set({
        "custom_etr_signed": 1,
        "custom_cu_serial_number": response.get("cu_serial_number", ""),
        "custom_cu_invoice_number": response.get("cu_invoice_number", ""),
        "custom_etr_verify_url": response.get("verify_url", ""),
        "custom_etr_sign_datetime": now_datetime(),
        "custom_etr_error": "",
    }, commit=True)
