# Copyright 2020 Trey, Kilobytes de Soluciones
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields
from odoo.tests.common import TransactionCase


class TestDeliveryPriceMethod(TransactionCase):

    def setUp(self):
        super().setUp()
        product_shipping_cost = self.env['product.product'].create({
            'type': 'service',
            'name': 'Shipping costs',
            'standard_price': 10,
            'list_price': 100,
        })
        self.carrier = self.env['delivery.carrier'].create({
            'name': 'Test carrier',
            'delivery_type': 'fixed',
            'product_id': product_shipping_cost.id,
            'fixed_price': 99.99,
        })

    def test_delivery_price_fixed(self):
        product = self.env.ref('product.product_delivery_01')
        partner = self.env.ref('base.res_partner_12')
        sale = self.env['sale.order'].create({
            'partner_id': partner.id,
            'carrier_id': self.carrier.id,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'product_uom_qty': 1})]
        })
        sale.get_delivery_price()
        self.assertEquals(sale.delivery_price, 99.99)
        sale.set_delivery_line()
        self.assertEquals(len(sale.order_line), 2)
        sale.action_confirm()
        picking = sale.picking_ids[0]
        self.assertEquals(len(picking.move_lines), 1)
        self.assertEquals(picking.carrier_id, self.carrier)
        picking.action_confirm()
        picking.action_assign()
        self.assertFalse(picking.carrier_price)
        picking.send_to_shipper()
        self.assertEquals(picking.carrier_price, 99.99)

    def test_delivery_price_method(self):
        product = self.env.ref('product.product_delivery_01')
        partner = self.env.ref('base.res_partner_12')
        sale = self.env['sale.order'].create({
            'partner_id': partner.id,
            'carrier_id': self.carrier.id,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'product_uom_qty': 1})]
        })
        self.carrier.write({
            'price_method': 'fixed',
            'fixed_price': 99.99,
        })
        sale.get_delivery_price()
        self.assertEquals(sale.delivery_price, 99.99)
        self.carrier.write({
            'price_method': 'fixed',
            'fixed_price': 5,
        })
        sale.get_delivery_price()
        self.assertEquals(sale.delivery_price, 5)
        self.carrier.write({
            'delivery_type': 'base_on_rule',
            'price_method': 'base_on_rule',
            'fixed_price': 99.99,
            'price_rule_ids': [(0, 0, {
                'variable': 'quantity',
                'operator': '==',
                'max_value': 1,
                'list_base_price': 11.11})]
        })
        sale.get_delivery_price()
        self.assertEquals(sale.delivery_price, 11.11)
