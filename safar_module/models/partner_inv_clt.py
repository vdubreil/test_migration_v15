# -*- coding: utf-8 -*-
from odoo import models, fields

class PartnerInvClt(models.Model):
    _name = 's_partner_inv_clt'
    _description = 'partner_inv_clt'
    _rec_name = 's_partner_id'

    s_partner_id = fields.Many2one('res.partner', string="Client")
    s_partner_id_cde = fields.Many2one('res.partner', string="Client qui a cdé")
    s_ca_avt_remise = fields.Monetary(string="CA avt remise", readonly=True)
    s_remise_importateur = fields.Monetary(string="Remise importateur", readonly=True)
    s_ca_apr_remise = fields.Monetary(string="CA apr remise", readonly=True)
    currency_id = fields.Many2one('res.currency', string="Currency")
    s_num_client_related = fields.Integer(related="s_partner_id_cde.s_num_client")