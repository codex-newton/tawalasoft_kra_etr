from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


FIELDS = {
    "Sales Invoice": [
        {"fieldname": "kra_etr_section", "label": "KRA ETR", "fieldtype": "Section Break",
         "insert_after": "amended_from", "collapsible": 1},
        {"fieldname": "custom_etr_signed", "label": "ETR Signed", "fieldtype": "Check",
         "insert_after": "kra_etr_section", "read_only": 1, "print_hide": 1},
        {"fieldname": "custom_cu_serial_number", "label": "CU Serial Number", "fieldtype": "Data",
         "insert_after": "custom_etr_signed", "read_only": 1},
        {"fieldname": "custom_cu_invoice_number", "label": "CU Invoice Number", "fieldtype": "Data",
         "insert_after": "custom_cu_serial_number", "read_only": 1},
        {"fieldname": "custom_etr_verify_url", "label": "Verify URL", "fieldtype": "Small Text",
         "insert_after": "custom_cu_invoice_number", "read_only": 1, "print_hide": 1},
        {"fieldname": "custom_etr_sign_datetime", "label": "ETR Signed At", "fieldtype": "Datetime",
         "insert_after": "custom_etr_verify_url", "read_only": 1, "print_hide": 1},
        {"fieldname": "custom_etr_error", "label": "ETR Last Error", "fieldtype": "Small Text",
         "insert_after": "custom_etr_sign_datetime", "read_only": 1, "print_hide": 1,
         "depends_on": "eval:doc.custom_etr_error"},
    ],
}


def setup_fields():
    create_custom_fields(FIELDS, ignore_validate=True)
