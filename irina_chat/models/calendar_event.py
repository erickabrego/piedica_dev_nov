from odoo import api, fields, models
from odoo.exceptions import ValidationError
import datetime
import requests

class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    @api.model
    def create(self, vals_list):
        res = super(CalendarEvent, self).create(vals_list)
        message = f"Su cita ha sido agendada con la fecha {res.start_date}"
        res.send_irina_message(message=message)
        return res


    def send_irina_message(self, message=None):
        for rec in self:
            url = f"https://app.irina.chat/api/v1/messages/send_template"
            token = self.env['ir.config_parameter'].sudo().get_param("irina.token")
            headers = {'Authorization': f'Bearer {token}'}
            partners = rec.partner_ids.filtered(lambda line: line.x_studio_es_paciente)
            for partner in partners:
                if partner.mobile:
                    message_data = {
                        "to": f"{partner.mobile}",
                        "waba": "106186548804243",
                        "number_id": "106586885430106",
                        "template_name": "piedica_confirmacion_cita",
                        "template_language": "es_mx",
                        "components": [
                            {
                                "type": "body",
                                "parameters": [
                                    {
                                        "type": "text",
                                        "text": f"{message}"
                                    },
                                    {
                                        "type": "text",
                                        "text": "COAPA"
                                    },
                                    {
                                        "type": "text",
                                        "text": "Mañana a la 1:00 PM"
                                    }
                                ]
                            },
                            {
                                'type': 'butonn',
                                'sub_type': 'quick_reply',
                                'index': '0',
                                'parameters': [
                                    {
                                        'type': 'payload',
                                        'payload': '/recordatorio_cita{\'event\':REMINDER\'}',
                                        'text': 'Crear recordatorio cita'
                                    }
                                ]
                            },
                            {
                                'type': 'butonn',
                                'sub_type': 'quick_reply',
                                'index': '1',
                                'parameters': [
                                    {
                                        'type': 'payload',
                                        'payload': '/ubicacion_sucursal{\'event\':LOCATION\'}',
                                        'text': 'Ver ubicación de sucursal'
                                    }
                                ]
                            }
                        ],
                        "contact": {
                            "name": f"{partner.name}",
                            "last_name": ""
                        }
                    }
                    response = requests.post(url, data=message_data, headers=headers)
                    print(response)
                else:
                    raise ValidationError("El paciente debe de tener un número móvil para comunicarse con él mediante whatsapp.")

    def notify_irina_before(self, events):
        for event in events:
            event.send_irina_message(f"Recuerda que tu cita es el {event.start_date}, lo esperamos.")