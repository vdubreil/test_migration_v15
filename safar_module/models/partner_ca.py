# -*- coding: utf-8 -*-
from odoo import models, fields

class PartnerCa(models.Model):
    _name = 's_partner_ca'
    _description = 'partner_ca'
    _rec_name = 's_year'

    s_partner_id = fields.Many2one('res.partner', string="Client")
    s_year = fields.Char(string='Année', readonly=True)
    s_ca = fields.Monetary(string="CA", readonly=True)
    currency_id = fields.Many2one('res.currency', string="Currency")