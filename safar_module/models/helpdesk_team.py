# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class HelpdeskTeam(models.Model):
    _inherit = 'helpdesk.team'

    s_int_send_mail = fields.Boolean()