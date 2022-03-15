# -*- coding: utf-8 -*-
from odoo import fields, models


class MailMessage(models.Model):
    _inherit = 'mail.message'

    def open_popup_form(self):
        self.ensure_one()
        if self.model and self.res_id:
            view_id = self.env[self.model].get_formview_id(self.res_id)
            return {
                'res_id': self.res_id,
                'res_model': self.model,
                'type': 'ir.actions.act_window',
                'views': [[view_id, 'form']],
            }