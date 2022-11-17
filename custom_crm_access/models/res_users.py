# -*- coding: utf-8 -*-
from odoo import api, fields, models

class ResUsers(models.Model):
    _inherit = "res.users"

    x_crm_team_ids = fields.Many2many(comodel_name="crm.team", string="Equipos de venta")