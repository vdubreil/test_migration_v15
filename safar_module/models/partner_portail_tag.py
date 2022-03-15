# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import fields, models, api, _


# Modèle pour gérer les listes d'étiquettes par espace de travail pour un client
class PartnerWorkspace(models.Model):
    _name = "s_partner_workspace"
    _description = "Partner_Workspace"
    _rec_name = "s_name"

    s_name = fields.Char()
    partner_id = fields.Many2one('res.partner', string="Client")
    folder_id = fields.Many2one("documents.folder", string="Espace de travail")
    facet_id = fields.Many2one("documents.facet", string="Catégorie d'étiquette")
    s_tag_ids = fields.Many2many('documents.tag', 'partner_workspace_tag_rel', string="Etiquettes autorisées")