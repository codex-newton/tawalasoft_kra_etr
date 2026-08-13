# Tawalasoft KRA ETR

ERPNext integration for KRA TIMS electronic tax register signing.

Signs Sales Invoices and credit notes against a TIMS-compliant control unit
middleware on submit, and writes the returned CU serial, CU invoice number and
verification URL back onto the invoice for printing.

- **Platform:** Frappe Framework v15 / ERPNext v15
- **Licence:** MIT
- **Publisher:** Tawalasoft Solutions

---

## Contents

- [What it does](#what-it-does)
- [How it works](#how-it-works)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Custom fields](#custom-fields)
- [Behaviour](#behaviour)
- [PIN resolution](#pin-resolution)
- [Price mode](#price-mode)
- [Payload reference](#payload-reference)
- [Print format](#print-format)
- [Troubleshooting](#troubleshooting)
- [Security notes](#security-notes)
- [Limitations](#limitations)

---

## What it does

Kenyan VAT-registered businesses must transmit invoices to KRA through a
certified control unit. This app connects ERPNext to a TIMS middleware that
fronts that control unit, so signing happens automatically when an invoice is
submitted rather than being re-keyed into a separate device.

**Provides**

- Automatic signing of Sales Invoices on submit
- Credit note signing, linked to the original signed invoice
- CU serial number, CU invoice number and verification URL stored per invoice
- Cancellation blocking once an invoice has been signed
- Manual retry from the invoice form when signing fails
- Format-validated buyer PIN resolution with a walk-in override

**Does not provide**

Stock or purchase transmission, Z-report handling, direct control unit
communication (the middleware handles that), or QR image generation.

---

## How it works

```
Sales Invoice submitted
         │
         ▼
  integration enabled?  ──no──► return
         │ yes
         ▼
  already signed?  ──yes──► return
         │ no
         ▼
  build payload  ◄──── seller PIN from Company.tax_id
         │        ◄──── buyer PIN via resolution chain
         │        ◄──── line items at inclusive or exclusive prices
         ▼
  POST to middleware /api/sign
         │
    ┌────┴────┐
    ▼         ▼
 success   failure
    │         │
    │         └─► log error, write custom_etr_error, invoice stays submitted
    ▼
 write CU serial, CU invoice number, verify URL, timestamp
```

**Signing is soft-fail by design.** A middleware outage must not stop the
business invoicing. The submit always succeeds; a failure is recorded on the
invoice and surfaced through a Retry button. The trade-off is that an unsigned
invoice can exist in a submitted state, so the error field needs monitoring.

---

## Requirements

| Requirement | Notes |
|---|---|
| ERPNext v15 | On Frappe Framework v15 |
| TIMS middleware | Reachable over HTTP from the ERPNext server |
| Basic auth credential | Issued by your middleware provider |
| Company tax ID | `Company.tax_id` must hold the seller KRA PIN |
| Python `requests` | Declared in `pyproject.toml` |

The middleware is a separate product supplied by your control unit vendor.
This app does not include or configure it.

---

## Installation

```bash
cd ~/frappe-bench

bench --site <site> backup

bench get-app <repository-url> tawalasoft_kra_etr
bench --site <site> install-app tawalasoft_kra_etr
bench --site <site> migrate
bench restart
```

Custom fields are created automatically by the `after_install` and
`after_migrate` hooks, so no manual field setup is needed.

---

## Configuration

Open **KRA ETR Settings** (a Single doctype).

| Field | Description |
|---|---|
| Enabled | Master switch. Leave off until the other fields are set and tested |
| Middleware URL | Base URL of your TIMS middleware, without a trailing path |
| Basic Auth Token | The value that follows `Basic ` in the Authorization header |
| Price Mode | `Exclusive` or `Inclusive` — must match how your item rates are entered |

The auth token is stored as a `Password` field: encrypted at rest with a
site-specific key, masked in the UI, and never returned by the REST API.

> **Settings do not promote between sites.** The encryption key is per-site, so
> a copied or fixtured record decrypts to garbage. Create the settings record
> by hand on each environment.

Enable only after confirming the URL and token against a test invoice.

---

## Custom fields

Added to Sales Invoice, all read-only, inside a collapsible **KRA ETR**
section:

| Fieldname | Type | Purpose |
|---|---|---|
| `custom_etr_signed` | Check | Signing succeeded |
| `custom_cu_serial_number` | Data | Control unit serial from the middleware |
| `custom_cu_invoice_number` | Data | CU invoice number, required on the printout |
| `custom_etr_verify_url` | Small Text | KRA verification URL, encoded into the QR |
| `custom_etr_sign_datetime` | Datetime | When signing completed |
| `custom_etr_error` | Small Text | Last failure reason, shown only when set |

Two further fields are referenced for signing to KRA when there is a walking customer. In this case, we are not using Point of Sale

| Fieldname | Doctype | Purpose |
|---|---|---|
| `custom_kra_pin` | Sales Invoice | Manual buyer PIN for walk-in sales |
| `custom_kra_pin` | Customer | Buyer PIN where `tax_id` is used for something else |

The code checks for each field's existence before reading it, so their absence
is harmless.

---

## Behaviour

### On submit

Signing is attempted when the integration is enabled and the invoice is not
already signed. Success writes the CU fields and clears any previous error;
failure logs a traceback, writes `custom_etr_error`, and leaves the invoice
submitted but unsigned.

### On cancel

Cancellation is **blocked** once an invoice is signed. A signed invoice has
been transmitted to KRA and cannot be withdrawn — issue a credit note instead.

### Credit notes

A return invoice is signed against the `credit-note` endpoint and must
reference an original invoice through Return Against. If that original has no
CU invoice number, submission is refused with an explanatory message: KRA
requires the credit note to reference the document it reverses.

### On validate

Converting an invoice to a return clears any inherited ETR fields, so a credit
note never carries the original's CU details.

### Manual retry

Submitted, unsigned invoices show a **Retry ETR Sign** button. It signs
immediately and reloads the form. The button is hidden once signing succeeds.

---

## PIN resolution

The buyer PIN is resolved in strict priority order:

1. `custom_kra_pin` on the Sales Invoice — an explicit manual entry wins
2. `Customer.tax_id`
3. `Customer.custom_kra_pin`
4. Empty — treated by TIMS as a walk-in sale

**Every source is format-validated** against `^[A-Z]\d{9}[A-Z]$`. A value that
fails the pattern falls through to the next source rather than being
transmitted. This is what stops placeholder data — `N/A`, `000000`,
`xxxxxxxxxxx` — reaching KRA, which a simple truthiness check would not catch.

The seller PIN comes from `Company.tax_id` and is normalised but not
format-validated, on the assumption that a misconfigured company PIN should
fail loudly at the middleware rather than silently become a walk-in sale.

---

## Price mode

| Mode | Value sent | Item fields used |
|---|---|---|
| Inclusive | 1 | `rate`, `amount` |
| Exclusive | 2 | `net_rate`, `net_amount` |

This must match how prices are entered in ERPNext. Getting it wrong produces
invoices whose declared tax does not reconcile — the totals will be internally
consistent but wrong against KRA's expectation.

---

## Payload reference

Sent to `/api/sign` as JSON:

| Field | Source |
|---|---|
| `invoice_date` | `posting_date`, formatted `DD_MM_YYYY` |
| `invoice_number` | Document name |
| `invoice_pin` | Seller PIN from Company |
| `customer_pin` | Resolved buyer PIN, may be empty |
| `customer_exid` | Reserved, always empty |
| `grand_total` | Absolute value, two decimals |
| `net_subtotal` | Absolute value, two decimals |
| `tax_total` | Absolute value, two decimals |
| `net_discount_total` | Absolute value, two decimals |
| `sel_currency` | Invoice currency, defaults to `KSH` |
| `rel_doc_number` | Original CU invoice number, credit notes only |
| `items_list` | Space-delimited lines, capped at 512 characters each |

Amounts use absolute values because credit notes carry negative totals in
ERPNext while TIMS expects positive figures on the credit-note endpoint.

Item descriptions are stripped of newlines, tabs and double quotes, which
would otherwise break the middleware's parsing.

---

## Print format

Kenyan law requires the CU invoice number and a verification QR code on the
printed invoice. Add to your print format:

```jinja
{% if doc.custom_etr_signed %}
  <img src="{{ qr_data_uri(doc.custom_etr_verify_url) }}"
       style="width:80px;height:80px;" />
  <div>CU: {{ doc.custom_cu_serial_number }}</div>
  <div>Inv#: {{ doc.custom_cu_invoice_number }}</div>
{% endif %}
```

If `qr_data_uri` is unavailable in your Frappe version, generate the QR through
another helper or a client-side library — this app does not bundle QR
generation.

---

## Troubleshooting

### Invoice submits but nothing is signed

Check that the integration is enabled in KRA ETR Settings. When disabled, the
handler returns immediately and writes no error.

### `custom_etr_error` is populated

Read the field on the invoice, then the full traceback:

**Error Log** → filter by title `KRA ETR sign failed`.

Common causes: middleware unreachable, wrong base URL, expired or wrong auth
token, seller PIN missing from the Company record.

### Cannot edit Middleware URL or Auth Token

The settings fields carry a permission level. If no permission row exists at
that level, the fields are inaccessible to every role. Add a matching
permission row, or remove the permlevel from the doctype.

### Credit note refuses to submit

The original invoice has no CU invoice number, meaning it was never signed.
Sign the original first — KRA requires the credit note to reference the
document it reverses.

### Signed invoice cannot be cancelled

Working as intended. Issue a credit note.

### Retry button missing

It appears only on submitted, unsigned invoices. A signed invoice or a draft
will not show it.

---

## Security notes

- The auth token is encrypted at rest and never written to source, logs or
  API responses
- The middleware URL and token live only in the settings record, not in code
- Middleware error responses are truncated to 500 characters before being
  stored on the invoice
- `retry_sign` is a whitelisted method; ensure it performs a permission check
  appropriate to your deployment before exposing the app to portal users

Never commit a real auth token, middleware hostname or tax PIN to this
repository. Configuration belongs in the settings record.

---

## Limitations

| Limitation | Impact |
|---|---|
| Signing is synchronous | A slow middleware delays the submit by up to the request timeout |
| Soft-fail on error | Unsigned submitted invoices are possible and need monitoring |
| No automatic retry | Failed signings require the manual button or a custom job |
| Sales Invoice only | Purchase and stock transmission are not implemented |
| No QR generation | The verification URL is stored; rendering is left to the print format |
| Seller PIN unvalidated | A malformed Company tax ID fails at the middleware, not at build time |

---

## Development

```bash
bench get-app <repository-url>
bench --site <site> install-app tawalasoft_kra_etr
bench --site <site> set-config developer_mode 1
```

Linting follows the Frappe convention — Ruff with tab indentation and
double quotes, configured in `pyproject.toml`. Pre-commit hooks and CI
workflows are included.

---

*Developed by Tawalasoft Solutions*