# -*- coding: utf-8 -*-
from odoo import models, fields

class PartnerOrigin(models.Model):
    _name = 's_partner_origin'
    _description = 'partner_origin'
    _rec_name = 's_name'

    s_name = fields.Char(string='Origine')