# tawalasoft_kra_etr

ERPNext integration with the KRA TIMS ETR middleware.

Signs Sales Invoices (and credit notes) on submit. Sync soft-fail: invoice
submits regardless; failures set `custom_etr_error` and expose a Retry button.

## Install

```bash
bench get-app <repo-url> tawalasoft_kra_etr
bench --site <site> install-app tawalasoft_kra_etr
bench --site <site> migrate
bench restart
```

## Configure

Open **KRA ETR Settings**:

- Middleware URL: `http://<host>:8084`
- Basic Auth Token: value after `Basic ` in the Authorization header
- Price Mode: `Exclusive` or `Inclusive`
- Enable when ready

Seller PIN comes from `Company.tax_id`. Customer PIN comes from `Customer.tax_id`.

## Print format QR

```jinja
{% if doc.custom_etr_signed %}
  <img src="{{ qr_data_uri(doc.custom_etr_verify_url) }}" style="width:80px;height:80px;" />
  <div>CU: {{ doc.custom_cu_serial_number }}</div>
  <div>Inv#: {{ doc.custom_cu_invoice_number }}</div>
{% endif %}
```