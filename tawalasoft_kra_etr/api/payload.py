import re

import frappe
from frappe.utils import flt, getdate


# KRA PIN format: one letter + 9 digits + one letter, e.g. P051515648L
KRA_PIN_RE = re.compile(r"^[A-Z]\d{9}[A-Z]$")

# Manual walk-in PIN override on Sales Invoice (custom field, label
# "Walk in Customer KRA Pin"). The companion field custom_walk_in_name holds
# the buyer name and is not part of the KRA payload.
WALK_IN_PIN_FIELD = "custom_kra_pin"


def _clean_pin(value):
	"""Normalise a PIN to uppercase with no spaces. Blank if unusable."""
	if value is None:
		return ""
	return re.sub(r"\s+", "", str(value)).upper()


def _valid_pin(value):
	"""Return the PIN only if it matches the KRA format, else empty string.

	This is what rejects placeholder junk like 'xxxxxxxxxxx', 'N/A', '000000',
	which would otherwise pass a simple truthiness check.
	"""
	pin = _clean_pin(value)
	return pin if KRA_PIN_RE.match(pin) else ""


def _si_walk_in_pin(doc):
	"""Manual PIN typed on the Sales Invoice, if the field exists and is filled."""
	if not frappe.get_meta("Sales Invoice").has_field(WALK_IN_PIN_FIELD):
		return ""
	return _valid_pin(doc.get(WALK_IN_PIN_FIELD))


def get_customer_pin(doc):
	"""Resolve the buyer PIN for the KRA payload.

	Priority:
	  1. Walk-in PIN typed on the Sales Invoice  (explicit, so it wins)
	  2. Customer.tax_id                         (only if a valid KRA PIN)
	  3. Customer.custom_kra_pin                 (only if a valid KRA PIN)
	  4. ""                                      (treated by TIMS as a walk-in sale)

	Every source is format-validated, so a placeholder value sitting in any of
	these fields falls through instead of being sent to KRA.
	"""
	pin = _si_walk_in_pin(doc)
	if pin:
		return pin

	customer = doc.get("customer")
	if not customer:
		return ""

	pin = _valid_pin(frappe.db.get_value("Customer", customer, "tax_id"))
	if pin:
		return pin

	if frappe.get_meta("Customer").has_field("custom_kra_pin"):
		pin = _valid_pin(frappe.db.get_value("Customer", customer, "custom_kra_pin"))
		if pin:
			return pin

	return ""


def build_sales_invoice_payload(doc, price_mode):
	"""price_mode: 1 = Inclusive, 2 = Exclusive"""
	seller_pin = _clean_pin(frappe.db.get_value("Company", doc.company, "tax_id"))
	customer_pin = get_customer_pin(doc)

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