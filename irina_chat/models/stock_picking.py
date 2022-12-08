from odoo import api, fields, models
import requests
import logging
_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = "stock.picking"

    def write(self, vals):
        res = super(StockPicking, self).write(vals)
        try:
            if vals.get("date_done"):
                for rec in self:
                    if rec.state == "done":
                        type_customer = rec._identify_type_customer()
                        template = False
                        if type_customer == "sucursal":
                            template = self.generate_irina_template("piedica_plantillas_listas", 6)
                        elif type_customer == "paciente":
                            template = self.generate_irina_template("piedica_plantillas_listas", 1)
                        if template:
                            self._send_irina_message(template)

        except Exception as error:
            _logger.info(error)
        return res

    def _identify_type_customer(self):
        rule = self.env["branch.factory"].sudo().search([("partner_id.id","=",self.partner_id.id)])
        if rule and self.picking_type_id.code == "incoming":
            return "sucursal"
        elif self.partner_id.x_studio_es_paciente and self.picking_type_id.code == "outgoing":
            return "paciente"
        else:
            return False

    def generate_irina_template(self, template, parameters):
        mobile = self._get_mobile_partner_irina()
        if mobile:
            waba = self.env['ir.config_parameter'].sudo().get_param("irina.waba")
            number_id = self.env['ir.config_parameter'].sudo().get_param("irina.number_id")

            components = [
                {
                    "type": "body",
                    "parameters": [
                        {
                            "type": "text",
                            "text": f"{self._get_name_partner_irina()}"
                        },
                    ]
                }
            ]

            if parameters == 6:
                components[0]["parameters"].append({
                    "type": "text",
                    "text": f"{','.join(self.move_ids_without_package.mapped('product_id').mapped('name'))}"
                })
                components[0]["parameters"].append({
                    "type": "text",
                    "text": f"{self.partner_id.contact_address_complete}"
                })
                components[0]["parameters"].append({
                    "type": "text",
                    "text": f"{self.date_done.strftime('%d-%m-%Y %H:%M:%S')}"
                })
                components[0]["parameters"].append({
                    "type": "text",
                    "text": f"{self.date_done.strftime('%d-%m-%Y %H:%M:%S')}"
                })
                components[0]["parameters"].append({
                    "type": "text",
                    "text": f"{self.partner_id.phone or self.partner_id.mobile}"
                })
            elif parameters == 1:
                components[0]["parameters"].append({
                    "type": "text",
                    "text": f"{self.carrier_tracking_ref}"
                })

            template_send = {
                "to": f"{str(mobile).replace(' ', '')}",
                "waba": waba,
                "number_id": number_id,
                "template_name": template,
                "template_language": "es_mx",
                "components": components,
                "contact": {
                    "name": f"{self._get_name_partner_irina()}",
                    "last_name": ""
                }
            }
            return template_send
        return False

    def _get_mobile_partner_irina(self):
        type_customer = self._identify_type_customer
        mobile = ""
        if type_customer == "sucursal":
            if self.sale_id:
                  mobile = self._format_mobile_number(self.sale_id.partner_id.mobile, self.sale_id.partner_id)
        elif type_customer == "paciente":
            mobile = self._format_mobile_number(self.partner_id.mobile, self.partner_id)
        return mobile

    def _get_name_partner_irina(self):
        type_customer = self._identify_type_customer
        name = ""
        if type_customer == "sucursal":
            if self.sale_id:
                  name = self.sale_id.partner_id.name
        elif type_customer == "paciente":
            name = self.partner_id.name
        return name


    def _format_mobile_number(self, mobile, contact):
        country_code = "52"
        if contact and contact.country_id.phone_code:
            country_code = contact.country_id.phone_code
        if f"+{country_code}" in mobile:
            mobile_number = mobile
        else:
            mobile_number = f"+{country_code}{mobile}"
        return mobile_number

    def _send_irina_message(self, template):
        url = f"https://app.irina.chat/api/v1/messages/send_template"
        token = self.env['ir.config_parameter'].sudo().get_param("irina.token")
        headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}
        try:
            response = requests.post(url, json=template, headers=headers)
            content = eval(response.content.decode('UTF-8'))
            _logger.info("DATOS ENVIADOS A IRINA")
            _logger.info(template)
            _logger.info("RESPUESTA IRINA")
            _logger.info(content)
        except Exception as error:
            _logger.info(error)



