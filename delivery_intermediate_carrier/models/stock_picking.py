# Copyright 2026 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _action_done(self):
        for item in self.filtered(lambda x: x.carrier_id):
            if item.carrier_id.is_intermediate:
                raise UserError(
                    self.env._(
                        "It is not possible to validate picking with an intermediate "
                        "carrier"
                    )
                )
        return super()._action_done()
