frappe.ui.form.on("Sales Invoice", {
   refresh(frm) {
       if (frm.doc.docstatus !== 1 || frm.doc.custom_etr_signed) return;
       frm.add_custom_button(__("Retry ETR Sign"), () => {
           frappe.call({
               method: "tawalasoft_kra_etr.api.sign.retry_sign",
               args: { sales_invoice: frm.doc.name },
               freeze: true,
               freeze_message: __("Signing..."),
               callback: (r) => {
                   if (!r.exc) frm.reload_doc();
               },
           });
       });
   },
});