# Copyright 2020 Tecnativa - David Vidal
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import _, fields, models
from odoo.exceptions import UserError
from .gls_asm_request import GlsAsmRequest
from .gls_asm_request import (
    GLS_ASM_SERVICES, GLS_SHIPPING_TIMES, GLS_POSTAGE_TYPE)


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    delivery_type = fields.Selection(selection_add=[("gls_asm", "GLS ASM")])
    gls_asm_uid = fields.Char(
        string="GLS UID",
    )
    gls_asm_service = fields.Selection(
        selection=GLS_ASM_SERVICES,
        string="GLS Service",
        help="Set the contracted GLS Service",
        default="1",  # Courier
    )
    gls_asm_shiptime = fields.Selection(
        selection=GLS_SHIPPING_TIMES,
        string="Shipping Time",
        help="Set the desired GLS shipping time for this carrier",
        default="0",  # 10h
    )
    gls_asm_postage_type = fields.Selection(
        selection=GLS_POSTAGE_TYPE,
        string="Postage Type",
        help="Postage type, usually 'Prepaid'",
        default="P",
    )

    def _gls_asm_uid(self):
        """The carrier can be put in test mode. The tests user must be set.
           A default given by GLS is put in the config parameter data """
        self.ensure_one()
        uid = (
            self.asm_user if self.prod_environment else
            self.env['ir.config_parameter'].sudo().get_param(
                'delivery_gls_asm.api_user_demo', ''))
        return uid

    def gls_asm_get_tracking_link(self, picking):
        """Provide tracking link for the customer"""
        tracking_url = ("http://www.asmred.com/extranet/public/"
                        "ExpedicionASM.aspx?codigo={}&cpDst={}")
        return tracking_url.format(
            picking.carrier_tracking_ref, picking.partner_id.zip)

    def _prepare_gls_asm_shipping(self, picking):
        """Convert picking values for asm api
        :param picking record with picking to send
        :returns dict values for the connector
        """
        self.ensure_one()
        # We can divide the picking into several delivery packages and a
        # label will be given for each one.
        package_number = len(picking.package_ids) or 1
        # A picking can be delivered from any warehouse
        sender_partner = (
            picking.picking_type_id.warehouse_id.partner_id or
            picking.company_id.partner_id)
        return {
            "fecha": fields.Date.today().strftime("%d/%m/%Y"),
            "portes": self.gls_asm_postage_type,
            "servicio": self.gls_asm_service,
            "horario": self.gls_asm_shiptime,
            "bultos": package_number,
            "peso": round(picking.shipping_weight, 3),
            "volumen": "",  # [optional] Volume, in m3
            "declarado": "",  # [optional]
            "dninomb": "0",  # [optional]
            "fechaentrega": "",  # [optional]
            "retorno": "0",  # [optional]
            "pod": "N",  # [optional]
            "podobligatorio": "N",  # [deprecated]
            "remite_plaza": "",  # [optional] Origin agency
            "remite_nombre": sender_partner.name,
            "remite_direccion": sender_partner.street or "",
            "remite_poblacion": sender_partner.city or "",
            "remite_provincia": sender_partner.state_id.name or "",
            "remite_pais": "34",  # [mandatory] always 34=Spain
            "remite_cp": sender_partner.zip or "",
            "remite_telefono": sender_partner.phone or "",
            "remite_movil": sender_partner.mobile or "",
            "remite_email": sender_partner.email or "",
            "remite_departamento": "",
            "remite_nif": sender_partner.vat or "",
            "remite_observaciones": "",
            "destinatario_codigo": "",
            "destinatario_plaza": "",
            "destinatario_nombre": (
                picking.partner_id.name or
                picking.partner_id.commercial_partner_id.name),
            "destinatario_direccion": picking.partner_id.street or "",
            "destinatario_poblacion": picking.partner_id.city or "",
            "destinatario_provincia": picking.partner_id.state_id.name or "",
            "destinatario_pais": (
                picking.partner_id.country_id.phone_code or ""),
            "destinatario_cp": picking.partner_id.zip,
            "destinatario_telefono": picking.partner_id.phone or "",
            "destinatario_movil": picking.partner_id.mobile or "",
            "destinatario_email": picking.partner_id.email or "",
            "destinatario_observaciones": "",
            "destinatario_att": "",
            "destinatario_departamento": "",
            "destinatario_nif": "",
            "referencia_c": picking.name,  # Our unique reference
            "referencia_0": "",  # Not used if the above is set
            "importes_debido": "0",  # The customer pays the shipping
            "importes_reembolso": "",  # TODO: Support Cash On Delivery
            "seguro": "0",  # [optional]
            "seguro_descripcion": "",  # [optional]
            "seguro_importe": "",  # [optional]
            "etiqueta": "PDF",  # Get Label in response
            "etiqueta_devolucion": "PDF",
            # [optional] GLS Customer Code
            # (when customer have several codes in GLS)
            "cliente_codigo": "",
            "cliente_plaza": "",
            "cliente_agente": "",
        }

    def gls_asm_send_shipping(self, pickings):
        """Send the package to GLS
        :param pickings: A recordset of pickings
        :return list: A list of dictionaries although in practice it's
        called one by one and only the first item in the dict is taken. Due
        to this design, we have to inject vals in the context to be able to
        add them to the message.
        """
        gls_request = GlsAsmRequest(self._gls_asm_uid())
        result = []
        for picking in pickings:
            vals = self._prepare_gls_asm_shipping(picking)
            # TODO: We don't have delivery rate
            vals.update({"tracking_number": False, "exact_price": 0})
            response = gls_request.GrabaServicios(vals)
            if not response or response.get("_return", -1) < 0:
                result.append(vals)
                continue
            # For compatibility we provide this number although we get
            # two more codes: codbarras and uid
            vals["tracking_number"] = response.get("_codexp")
            picking.gls_asm_public_tracking_ref = response.get("_codbarras")
            # Pass values by context to inject in the mail
            ctx = {
                "gls_asm_shipping": True,
                "gls_barcode": response.get("_codbarras"),
            }
            if response.get("gls_label"):
                ctx["gls_label"] = response.get("gls_label")
                ctx["gls_label_name"] = "gls_label_{}.pdf".format(
                    response.get("_codbarras"))
            self.env.context = dict(self.env.context, **ctx)
            result.append(vals)
        return result

    def gls_asm_cancel_shipment(self, pickings):
        """Cancel the expedition"""
        gls_request = GlsAsmRequest(self._gls_asm_uid())
        for picking in pickings.filtered("carrier_tracking_ref"):
            response = gls_request.Anula(
                picking.carrier_tracking_ref)
            if not response or response.get("_return") < 0:
                msg = _(
                    "GLS Cancellation failed with reason: %s" %
                    response.get("value", "Connection Error"))
                if len(pickings) > 1:
                    picking.message_post(body=msg)
                    continue
                raise UserError(msg)
            # TODO: Integrate with delivery_carrier_state
            picking.gls_asm_public_tracking_ref = False
            picking.message_post(body=_(
                "GLS Expedition with reference %s cancelled") %
                picking.carrier_tracking_ref)

    def gls_asm_get_label(self, gls_asm_public_tracking_ref):
        """Generate label for picking
        :param picking - stock.picking record
        :returns pdf file
        """
        self.ensure_one()
        if not gls_asm_public_tracking_ref:
            return False
        gls_request = GlsAsmRequest(self._gls_asm_uid())
        label = gls_request.EtiquetaEnvio(gls_asm_public_tracking_ref)
        if not label:
            return False
        return label

    def action_get_manifest(self):
        """Action to launch the manifest wizard"""
        self.ensure_one()
        wizard = self.env["gls.asm.minifest.wizard"].create({
            "carrier_id": self.id})
        view_id = self.env.ref(
            "delivery_gls_asm.delivery_manifest_wizard_form"
        ).id
        return {
            "name": _("GLS Manifest"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "gls.asm.minifest.wizard",
            "view_id": view_id,
            "views": [(view_id, "form")],
            "target": "new",
            "res_id": wizard.id,
            "context": self.env.context,
        }
