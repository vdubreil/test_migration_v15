# -*- coding: utf-8 -*-
from odoo import models, fields

class PartnerTop(models.Model):
    _name = 's_partner_top'
    _description = 'partner_top'
    _rec_name = 's_partner_id'

    s_product_id = fields.Many2one('product.product', string="Article", readonly=True)
    s_partner_id = fields.Many2one('res.partner', string="Client")
    s_qte = fields.Float(string="Quantité", readonly=True)
    s_ca = fields.Monetary(string="CA", readonly=True)
    currency_id = fields.Many2one('res.currency', string="Currency")
    s_dt_min = fields.Datetime(string="Dt Min", readonly=True)
    s_dt_max = fields.Datetime(string="Dt Max", readonly=True)