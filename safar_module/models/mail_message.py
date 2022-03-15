# -*- coding: utf-8 -*-
from odoo import fields, models, api


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

    # Attention, cette fonction bypass la fonction surchargée que l'on trouve dans le fichier mail_message.py d'Odoo qui ajoutait un contrôle pour
    # empêcher la lecture groupée lorsque l'utilisateur n'est pas administrateur
    # La fonction bypassée ne faisait que ce contrôle pour l'instant donc la bypasser n'est pas génant
    # Mais si à l'avenir elle faisait autre chose, alors Odoo Safar n'en profitera pas
    @api.model
    def _read_group_raw(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        return super(models.Model, self)._read_group_raw(
            domain=domain, fields=fields, groupby=groupby, offset=offset,
            limit=limit, orderby=orderby, lazy=lazy,
        )