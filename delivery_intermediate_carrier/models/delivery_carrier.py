# Copyright 2026 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    is_intermediate = fields.Boolean(
        string="Is intermediate?",
        help="If it is defined as 'intermediate', you will not be able to confirm "
        "a picking with this carrier",
    )
