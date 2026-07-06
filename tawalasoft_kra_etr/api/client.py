import frappe
import requests
from frappe import _


class KRAETRClient:
    def __init__(self):
        settings = frappe.get_single("KRA ETR Settings")
        if not settings.enabled:
            frappe.throw(_("KRA ETR integration is disabled"))
        if not settings.middleware_url:
            frappe.throw(_("KRA ETR Settings: Middleware URL not configured"))
        self.base_url = settings.middleware_url.rstrip("/")
        self.auth_token = settings.get_password("auth_token")

    def sign(self, doc_type, price_mode, payload):
        url = f"{self.base_url}/api/sign?{doc_type}+{price_mode}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {self.auth_token}",
        }
        r = requests.post(url, headers=headers, json=payload, timeout=30)
        r.raise_for_status()
        return r.json()
