# -*- coding: utf-8 -*-
from odoo import models, fields


class MrpBox(models.Model):
    _name = 's_mrp_box'
    _description = 'Box pour OF'
    _rec_name = 's_name'

    s_name = fields.Char(string='Nom')
    s_tab_of = fields.One2many('mrp.production', 's_id_box', 'Ordres de fabrication')
    s_id_box_transfert = fields.Many2one('s_mrp_box', string="Transférer ces OF dans le Box")

    def call_move_of(self):
        # on transfert chaque OF lié à ce Box vers le Box choisi dans le m2o
        for of in self.s_tab_of:
            of.s_id_box = self.s_id_box_transfert.id

        # et on vide le champ de transfert pour faire disparaître le bouton de transfert
        self.s_id_box_transfert = False

    def call_clean_box(self):
        # on vide manuellement un box au cas où des OF resteraient coincés dedans
        for of in self.s_tab_of:
            of.s_id_box = False