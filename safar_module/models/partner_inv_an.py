# -*- coding: utf-8 -*-
from odoo import models, fields

class PartnerInvAn(models.Model):
    _name = 's_partner_inv_an'
    _description = 'partner_inv_an'
    _rec_name = 's_year'

    s_partner_id = fields.Many2one('res.partner', string="Client")
    s_year = fields.Char(string='Année', readonly=True)
    s_ca_avt_remise = fields.Monetary(string="CA avt remise", readonly=True)
    s_remise_importateur = fields.Monetary(string="Remise importateur", readonly=True)
    s_ca_apr_remise = fields.Monetary(string="CA apr remise", readonly=True)
    currency_id = fields.Many2one('res.currency', string="Currency")