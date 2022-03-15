# -*- coding: utf-8 -*-
from odoo import models, fields


class Photo_article(models.Model):
    _name = 's_photo_article'
    _description = 'photo_article'
    _rec_name = 's_name'

    s_name = fields.Char(string="Nom")
    s_article = fields.Many2one('product.template', string='Article')
    s_photo = fields.Binary(string='Photo')
    s_photo_filename = fields.Char()
