# -*- coding: utf-8 -*-
from odoo import fields, models, api
from bs4 import BeautifulSoup

class MailMessage(models.Model):
    _inherit = 'mail.message'

    s_valide = fields.Char(string='Validité')
    s_type_contact = fields.Char(string='Type Contact')

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

    @api.model
    def create(self, values):
        res = super(MailMessage, self).create(values)
        if res:
            res.determine_type_contact_et_validite()
        return res

    def write(self, values):
        res = super(MailMessage, self).write(values)
        if res:
            self.determine_type_contact_et_validite()
        return res

    def determine_type_contact_et_validite(self):
        values = {}
        nature = ""
        statut = ""
        type_contact = ""
        if self.model == 'res.partner' and self.res_id:
            partner = self.env['res.partner'].search([('id', '=', self.res_id)])
            if partner:
                if partner.parent_id:
                    nature = partner.parent_id.s_nature_client
                    statut = partner.parent_id.s_status_client
                else:
                    nature = partner.s_nature_client
                    statut = partner.s_status_client

        if self.model == 'crm.lead' and self.res_id:
            lead = self.env['crm.lead'].search([('id', '=', self.res_id)])
            if lead:
                if lead.partner_id:
                    if lead.partner_id.parent_id:
                        nature = lead.partner_id.parent_id.s_nature_client
                        statut = lead.partner_id.parent_id.s_status_client
                    else:
                        nature = lead.partner_id.s_nature_client
                        statut = lead.partner_id.s_status_client
                else:
                    type_contact = 'Prospect'

        if nature == 'reseau':
            type_contact = 'Client'
        elif nature == 'importateur':
            type_contact = 'Importateur'
        elif nature == 'direct':
            if statut == 'actif':
                type_contact = 'Client'
            elif statut == 'inactif':
                type_contact = 'Prospect'
        else:
            if statut == 'actif':
                type_contact = 'Client'
            elif statut == 'inactif':
                type_contact = 'Prospect'

        if type_contact:
            values['s_type_contact'] = type_contact

        # Validité du compte-rendu
        if self.model == 'res.partner' or self.model == 'crm.lead':
            nb_car_mini = int(self.env['ir.config_parameter'].get_param('nb.car.min.pour.compte.rendu.valide'))
            if self.body:
                nb_car = 0
                mem_car = ""

                soup = BeautifulSoup(self.body, "lxml")

                for car in soup.get_text():
                    if car == " " and mem_car == " " or car == '\n':
                        continue
                    else:
                        nb_car += 1
                        mem_car = car

                if nb_car >= nb_car_mini:
                    values['s_valide'] = 'Valide'
                if nb_car < nb_car_mini:
                    values['s_valide'] = f'Non Valide (Moins de {nb_car_mini} caractères)'
            else:
                values['s_valide'] = f'Non Valide (Moins de {nb_car_mini} caractères)'

        return super(MailMessage, self).write(values)

    # initialisation des champs s_type_contact et s_valide
    def init_s_type_contact(self):
        messages = self.env['mail.message'].search(['|', ('model', '=', 'res.partner'), ('model', '=', 'crm.lead')])
        if messages:
            i = 0
            for message in messages:
                message.determine_type_contact_et_validite()
                i += 1