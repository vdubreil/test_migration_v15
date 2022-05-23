# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    @api.model
    def create(self, values):
        res = super(HelpdeskTicket, self).create(values)
        if res:
            if not res.user_id:
                pass
                list_partner = []
                team = self.env['helpdesk.team'].search([('id', '=', res.team_id.id)])
                if team:
                    if team.s_int_send_mail:
                        if team.member_ids:
                            for member in team.member_ids:
                                if member.partner_id:
                                    list_partner.append(member.partner_id.id)

                if list_partner:
                    res.message_post(
                        body='Un nouveau ticket est rattaché à votre groupe, merci de le traiter au plus vite.',
                        subject=_('Nouveau Ticket : %s') % (res.display_name,), partner_ids=list_partner,
                        message_type='email')
        return res