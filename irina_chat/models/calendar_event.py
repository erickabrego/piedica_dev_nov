# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError
import requests
import logging
_logger = logging.getLogger(__name__)

class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    x_contact_irina = fields.Char(string="Contacto irina")

    #---------------------------------------Métodos CRUD---------------------------------------------------------

    @api.model
    def create(self, vals_list):
        res = super(CalendarEvent, self).create(vals_list)
        #Se envia mensaje de cita agendada
        res.send_irina_message(template="piedica_confirmacion_cita")
        return res

    def write(self, vals):
        res = super(CalendarEvent, self).write(vals)
        for rec in self:
            #Si la cita se confirma
            if vals.get("x_studio_paciente_confirm_asistencia"):
                if rec.x_studio_paciente_confirm_asistencia:
                    #Se envia mensaje de confirmación
                    rec.send_irina_message(template="piedica_confirmacion_cita")
            # Si la cita se se cancela
            if vals.get("x_studio_paciente_cancel_cita"):
                if rec.x_studio_paciente_cancel_cita:
                    # Se envia mensaje de no asistio
                    rec.send_irina_message(template="piedica_confirmacion_cita")
            # Si se asiste a la cita
            if vals.get("x_studio_paciente_asisti_a_cita"):
                if rec.x_studio_paciente_asisti_a_cita:
                    # Se envia mensaje de asistio
                    rec.send_irina_message(template="piedica_confirmacion_cita")
        return res

    #--------------------------------------Métodos de clase------------------------------------------------------


    #Envio de mensajes a Irina
    def send_irina_message(self, template=None):
        for rec in self:
            url = f"https://app.irina.chat/api/v1/messages/send_template"
            token = self.env['ir.config_parameter'].sudo().get_param("irina.token")
            waba = self.env['ir.config_parameter'].sudo().get_param("irina.waba")
            number_id = self.env['ir.config_parameter'].sudo().get_param("irina.number_id")
            headers = {'Content-Type': 'application/json','Authorization': f'Bearer {token}'}
            #Se obtiene el contacto del paciente o pacientes
            partners = rec.partner_ids.filtered(lambda line: line.x_studio_es_paciente)
            for partner in partners:
                #Se verifica que el paciente tenga celular
                if partner.mobile:
                    message_data = {
                        "to": f"{str(partner.mobile).replace(' ','')}",
                        "waba": waba,
                        "number_id": number_id,
                        "template_name": template,
                        "template_language": "es_mx",
                        "components": [
                            {
                                "type": "body",
                                "parameters": [
                                    {
                                        "type": "text",
                                        "text": f"{partner.name}"
                                    },
                                    {
                                        "type": "text",
                                        "text": f"{rec.x_studio_sucursal}"
                                    },
                                    {
                                        "type": "text",
                                        "text": f"{rec.user_id.name}"
                                    },
                                    {
                                        "type": "text",
                                        "text": f"{rec.start.strftime('%d-%b-%Y %I.%M %p')}"
                                    }
                                ]
                            },
                            {
                                "type": 'button',
                                "sub_type": 'url',
                                "index": '0',
                                "parameters": [
                                    {
                                        'type': 'text',
                                        'text': f'{rec.generate_address_url()}'
                                    }
                                ]
                            },
                        ],
                        "contact": {
                            "name": f"{partner.name}",
                            "last_name": ""
                        }
                    }
                    try:
                        response = requests.post(url, json=message_data, headers=headers)
                        content = response.content.decode('UTF-8')
                        rec.x_contact_irina = content.get("contact_id") if content else False
                        _logger.info("DATOS ENVIADOS A IRINA")
                        _logger.info(message_data)
                        _logger.info("RESPUESTA IRINA")
                        _logger.info(response.content)
                    except Exception as error:
                        _logger.info(error)
                else:
                    raise ValidationError("El paciente debe de tener un número móvil para comunicarse con él mediante whatsapp.")

    def notify_irina_before(self, events):
        for event in events:
            event.send_irina_message(template="piedica_confirmacion_cita")

    def notify_tips(self):
        for rec in self:
            rec.send_irina_message(template="piedica_confirmacion_cita")

    def generate_address_url(self):
        #Eliminar las tildes de nuestra cadena
        a, b = 'áéíóúüñÁÉÍÓÚÜÑ', 'aeiouunAEIOUUN'
        trans = str.maketrans(a, b)
        #Iniciamos el query de nuestra url
        maps_url = "?q="
        #Obtenemos la dirección de la sucursal
        location = self.appointment_type_id.location
        location = "".join(ch for ch in location if ch.isalnum() or str(ch).isspace())
        if location:
            maps_url += str(location).replace(" ","+")
        maps_url = maps_url.translate(trans)
        return maps_url.strip()


