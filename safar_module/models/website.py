from odoo import fields, models

class Website(models.Model):
    _inherit = 'website'

    s_page_histoire = fields.Char()
    s_page_valeur = fields.Char()
    s_page_certification = fields.Char()
    s_page_job = fields.Char()
    s_page_mention = fields.Char()
    s_page_politique = fields.Char()