# Copyright 2020 Tecnativa - David Vidal
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    # ASM API has two references for each delivery. This one is needed
    # for some operations like getting the label
    gls_asm_public_tracking_ref = fields.Char(
        string="GLS Barcode",
        readonly=True,
        copy=False,
    )

    def message_post(self, **kwargs):
        """Inject GLS values in shipping message"""
        if not self.env.context.get("gls_asm_shipping"):
            return super().message_post(**kwargs)
        body = kwargs.get("body", "")
        body += "\nbarcode: {}".format(
            self.env.context.get("gls_barcode")
        )
        attachment = []
        if self.env.context.get("gls_label"):
            attachment.append((
                self.env.context.get("gls_label_name", "gls_label.pdf"),
                self.env.context["gls_label"]))
        return super().message_post(body=body, attachments=attachment)

    def gls_asm_get_label(self):
        """Get GLS Label for this picking expedition"""
        self.ensure_one()
        if (self.delivery_type != "gls_asm" or not
                self.gls_asm_public_tracking_ref):
            return
        pdf = self.carrier_id.gls_asm_get_label(
            self.gls_asm_public_tracking_ref)
        label_name = "gls_{}.pdf".format(
            self.gls_asm_public_tracking_ref, "PDF")
        self.message_post(
            body=("GLS label for %s" % self.gls_asm_public_tracking_ref),
            attachments=[(label_name, pdf)],
        )
