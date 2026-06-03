# Copyright 2026 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.exceptions import UserError
from odoo.tests import Form

from odoo.addons.base.tests.common import BaseCommon


class TestDeliveryIntermediateCarrier(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        service_product = cls.env["product.product"].create(
            {
                "name": "Test service product",
                "type": "service",
            }
        )
        cls.carrier_not_intermediate = cls.env["delivery.carrier"].create(
            {
                "name": "Test carrier (not intermediate)",
                "product_id": service_product.id,
            }
        )
        cls.carrier_intermediate = cls.env["delivery.carrier"].create(
            {
                "name": "Test carrier (intermediate)",
                "is_intermediate": True,
                "product_id": service_product.id,
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Test product",
                "type": "consu",
            }
        )
        cls.partner = cls.env["res.partner"].create({"name": "Test partner"})
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)], limit=1
        )
        picking_form = Form(
            cls.env["stock.picking"].with_context(
                default_picking_type_id=cls.warehouse.out_type_id.id,
            )
        )
        picking_form.partner_id = cls.partner
        with picking_form.move_ids_without_package.new() as line_form:
            line_form.product_id = cls.product
            line_form.product_uom_qty = 1
        cls.picking = picking_form.save()
        cls.picking.action_confirm()

    def test_picking_done_carrier_not_intermediate(self):
        self.picking.carrier_id = self.carrier_not_intermediate
        self.picking.button_validate()
        self.assertEqual(self.picking.state, "done")

    def test_picking_done_carrier_intermediate(self):
        self.picking.carrier_id = self.carrier_intermediate
        msg = "It is not possible to validate picking with an intermediate"
        "carrier"  # pylint: disable=W0105
        with self.assertRaisesRegex(UserError, msg):
            self.picking.button_validate()
