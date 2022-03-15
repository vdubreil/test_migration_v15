# -*- coding: utf-8 -*-
from odoo import fields, models, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    s_code_concession = fields.Many2one('res.partner', string="Code concession de")
    s_code_concession_related = fields.Char(related="s_code_concession.s_code_concession", store="True", string="Code concession lié")
    # s_id_client_facture = fields.Integer(related="partner_invoice_id.id", store="True",
    #                                      string="Id client facture")
    s_client_facture_related = fields.Char(related="partner_invoice_id.name", store="false")
    s_interlocuteur = fields.Many2one('res.partner', string="Interlocuteur")
    s_interlocuteur_email = fields.Char(related="s_interlocuteur.email")
    s_configuration_exist = fields.Boolean(compute="compute_configuration_existe", store="True", string="Présence d'une config dans la cde")
    s_no_ligne_commande_exist = fields.Boolean(compute="compute_no_ligne_commande_existe", store="True", string="Présence d'un n° de ligne dans la cde")
    s_num_clt_facture_related = fields.Integer(related="partner_invoice_id.s_num_client", store="False")
    s_jr_facturation_related = fields.Selection(related="partner_invoice_id.s_jr_facturation", store="False", string="Num Jr Facturation")
    s_edi_data = fields.Text(string="Données EDI")
    s_id_famille_client_related = fields.Many2one(related="partner_id.s_id_famille_client", store="false")

    """CODE récupéré depuis application achetée sur le store 'Sale order quick MRP information'"""
    sh_mrp_ids = fields.Many2many(
        comodel_name='mrp.production',
        string="Ordre de fabrication",
        compute='_compute_mrp_orders'
    )

    mrp_count = fields.Integer(
        string="Ordres de fabrication",
        compute='_compute_mrp_count'
    )
    """Fin du code acheté"""

    @api.model
    def create(self, values):
        record = super(SaleOrder, self).create(values)
        if record:
            if not record.global_channel_id:
                # On force le global channel à la valeur par défaut paramétrée dans la fiche sté
                channel_par_defaut = False
                company = self.env['res.company'].search([('id', '=', record.company_id.id)])
                if company:
                    if company.s_global_channel_par_defaut:
                        channel_par_defaut = company.s_global_channel_par_defaut.id
                        record['global_channel_id'] = channel_par_defaut

        return record



    # Calcul le CA annuel pour tous les clients ou celui passé en paramètre
    def calcul_ca_cde_year(self, idclt=False):
        # on regarde s'il faut construire des paramètres spécifiques pour le client si passé en paramètre
        param_clt1 = ""
        param_clt2 = ""
        if idclt:
            param_clt1 = " and so.partner_id = " + str(idclt)
            param_clt2 = " WHERE s_partner_id = " + str(idclt)

        # on vide la table
        self.env.cr.execute('DELETE FROM s_partner_ca' + str(param_clt2))

        # on récupère les aggrégats par une rqte
        self.env.cr.execute("""
            INSERT INTO s_partner_ca(s_partner_id, currency_id, s_year, s_ca)
            SELECT partner_id, pr.currency_id, to_char(date_order,'YYYY'), sum(so.amount_untaxed)
            FROM SALE_ORDER AS so
            LEFT JOIN PRODUCT_PRICELIST AS pr on so.pricelist_id = pr.id
            WHERE so.state in ('sale', 'done') """ + param_clt1 + """
            GROUP BY partner_id, pr.currency_id, to_char(date_order,'YYYY')
        """)

    # Calcul du palmarès des ventes d'articles pour tous les clients ou le client/période passé en paramètre
    def calcul_top_cde(self, idclt=False):
        # paramètre du nb de jours glissants pour déterminer la période par défaut
        nb_jr_glissant = self.env['ir.config_parameter'].get_param('nb.jr.glissant.palmares')
        if not nb_jr_glissant:
            nb_jr_glissant = 365
        nb_jr_glissant = nb_jr_glissant - 1  # on enlève un jour car le jour en cours est pris en compte

        # paramètre client
        param_clt1 = ""
        param_clt2 = ""
        if idclt:  # appel depuis bouton recalculer de la fiche client
            param_clt1 = " and so.partner_id = " + str(idclt)
            param_clt2 = " WHERE s_partner_id = " + str(idclt)
        else:
            # on est sur tous les clients donc en traitement de nuit, donc on remet tous les clients sur une année glissante
            self.env.cr.execute(
                "UPDATE res_partner SET s_period_from = NOW() - INTERVAL '" + str(nb_jr_glissant) + " DAY' ")
            self.env.cr.execute("UPDATE res_partner SET s_period_to = NOW() ")

        # on vide la table des données de tous les clients ou du client passé en paramètre
        self.env.cr.execute("DELETE FROM s_partner_top " + str(param_clt2))

        # on passe une rqte pour calculer le palmarès de tous les clients ou du client passé en paramètre
        self.env.cr.execute("""
            INSERT INTO s_partner_top(s_partner_id,s_product_id,currency_id,s_qte,s_ca,s_dt_min,s_dt_max)
            SELECT so.partner_id, sol.product_id, sol.currency_id, sum(sol.product_uom_qty) as qty, sum(sol.price_subtotal) as ca, min(so.date_order) as dtmin, max(so.date_order) as dtmax
            FROM sale_order AS so
            INNER JOIN sale_order_line AS sol ON so.id=sol.order_id
            INNER JOIN res_partner AS pa ON so.partner_id = pa.id
            WHERE so.state in ('sale', 'done') 
            AND DATE(so.date_order) >= COALESCE(pa.s_period_from, NOW() - INTERVAL '""" + str(nb_jr_glissant) + """ DAY') AND DATE(so.date_order) <= COALESCE(pa.s_period_to,NOW())
            """ + param_clt1 + """
            GROUP BY so.partner_id, sol.product_id, sol.currency_id
            ORDER BY sum(sol.product_uom_qty) DESC, sum(sol.price_subtotal) DESC
        """)

    # Effectue une copie de la cde à la demande du client via son portail
    def action_duplicate(self, values):
        record = super(SaleOrder, self).copy(values)
        if record:
            for line in record.order_line:
                line.product_id_change()  # fonction à la ligne qui recalcule le pu et les montants

            record._amount_all()  # fonction à l'entête qui recalcule les montants de la cde

        return record

    @api.onchange('partner_shipping_id')
    def onchange_partner_shipping_id(self):
        if self.partner_shipping_id.s_code_concession:
            self.s_code_concession = self.partner_shipping_id if self.partner_shipping_id else self.partner_id
        else:
            self.s_code_concession = self.partner_id if self.partner_id else False

    @api.onchange('partner_invoice_id')
    def onchange_partner_invoice_id(self):
        """search = self.env['res.partner'].search(['&', ('s_id_client_facture', '=', self.partner_invoice_id.id),
                                                 ('id', 'child_of', self.partner_id.id)],
                                                limit=1)
        self.s_code_concession = search if search else self.partner_invoice_id"""
        self.payment_term_id = self.partner_invoice_id.property_payment_term_id
        self.pricelist_id = self.partner_invoice_id.property_product_pricelist
        self.fiscal_position_id = self.partner_invoice_id.property_account_position_id

    @api.onchange('s_code_concession')
    def onchange_s_code_concession(self):
        self.partner_invoice_id = self.s_code_concession.s_id_client_facture \
            if self.s_code_concession.s_id_client_facture \
            else self.s_code_concession

    """Overide the function to add s_code_concession and change partner_invoice_id base value"""
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        # res = super(SaleOrder, self).onchange_partner_id()
        """
        Update the following fields when the partner is changed:
        - Pricelist
        - Payment terms
        - Invoice address
        - Delivery address
        - Code concession
        """
        if not self.partner_id:
            self.update({
                'payment_term_id': False,
                'partner_invoice_id': False,
                'partner_shipping_id': False,
                'fiscal_position_id': False,
                's_code_concession': False,
            })
            return

        addr = self.partner_id.address_get(['delivery', 'invoice', 'contact'])
        partner_user = self.partner_id.user_id or self.partner_id.commercial_partner_id.user_id
        values = {
            'partner_shipping_id': addr['contact'],
            'payment_term_id':
                self.partner_invoice_id.property_payment_term_id if
                self.partner_invoice_id.property_payment_term_id else
                self.partner_id.property_payment_term_id,
        }
        user_id = partner_user.id or self.env.uid
        if self.user_id.id != user_id:
            values['user_id'] = user_id

        if self.env['ir.config_parameter'].sudo().get_param('account.use_invoice_terms') and self.env.company.invoice_terms:
            values['note'] = self.with_context(lang=self.partner_id.lang).env.company.invoice_terms

        values['team_id'] = self.env['crm.team']._get_default_team_id(user_id=user_id)
        self.update(values)

    """Ouvre le configurateur SAFAR dans une nouvelle fenetre"""
    def call_safar_config_saleorder(self):
        url_site = self.env['ir.config_parameter'].get_param('url.configurateur')
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': url_site + '?client="' +
                   str(self.partner_id.s_num_client) + '"&invoiceId="' + str(self.id) + '"',
        }

    """Ouvre une vue modale (wizzard) pour rechercher un product dans une pricelist"""
    def open_search_item_pricelist_view(self):
        for order in self:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Chercher un produit par sa référence client',
                'res_model': 'product.pricelist',
                'view_type': 'tree',
                'view_mode': 'tree',
                'res_id': order.pricelist_id,
                'view_id': self.env.ref('safar_module.s_product_pricelist_item_tree_view', False).id,
                'target': 'new',
            }

    """Vérifie dans toutes les lignes de la cde, si il y a au moins une configuration de renseignée"""
    @api.depends('order_line', 'order_line.s_configuration')
    def compute_configuration_existe(self):
        for record in self:
            configuration_exist = False
            for line in record.order_line:
                if line.s_configuration:
                    configuration_exist = True
                    break

            record.update({'s_configuration_exist': configuration_exist})

    """Vérifie dans toutes les lignes de la cde, si il y a au moins un numéro de ligne de renseigné"""
    @api.depends('order_line', 'order_line.s_no_ligne_commande')
    def compute_no_ligne_commande_existe(self):
        for record in self:
            no_ligne_cde_exist = False
            for line in record.order_line:
                if line.s_no_ligne_commande:
                    no_ligne_cde_exist = True
                    break

            record.update({'s_no_ligne_commande_exist': no_ligne_cde_exist})

            # def action_view_of(self):
    #     invoices = self.mapped('invoice_ids')
    #     action = self.env.ref('account.action_move_out_invoice_type').read()[0]
    #     if len(invoices) > 1:
    #         action['domain'] = [('id', 'in', invoices.ids)]
    #     elif len(invoices) == 1:
    #         form_view = [(self.env.ref('account.view_move_form').id,'form')]
    #         if 'views' in action:
    #             action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
    #         else:
    #             action['views'] = form_view
    #         action['res_id'] = invoices.id
    #     else:
    #         action = {'type': 'ir.actions.act_window_close'}
    #
    #     context = {
    #         'default_type': 'out_invoice',
    #     }
    #     if len(self) == 1:
    #         context.update({
    #             'default_partner_id': self.partner_id.id,
    #             'default_partner_shipping_id': self.partner_shipping_id.id,
    #             'default_invoice_payment_term_id': self.payment_term_id.id or self.partner_id.property_payment_term_id.id or
    #                 self.env['account.move'].default_get(['invoice_payment_term_id']).get('invoice_payment_term_id'),
    #             'default_invoice_origin': self.mapped('name'),
    #             'default_user_id': self.user_id.id,
    #         })
    #     action['context'] = context
    #     return action

    """CODE récupéré depuis application achetée sur le store 'Sale order quick MRP information'"""
    def _compute_mrp_count(self):
        if self:
            for rec in self:
                mrp_orders = self.env['mrp.production'].sudo().search([
                    ('origin', '=', rec.name)
                ])
                if mrp_orders:
                    rec.mrp_count = len(mrp_orders.ids)
                else:
                    rec.mrp_count = 0

    def action_view_manufacturing(self):
        return {
            'name': 'Manufacturing Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.production',
            'view_mode': 'tree,form',
            'domain': [('origin', '=', self.name)],
            'target': 'current'
        }

    def _compute_mrp_orders(self):
        if self:
            for rec in self:
                mrp_orders = self.env['mrp.production'].sudo().search([
                    ('origin', '=', rec.name)
                ])
                if mrp_orders:
                    rec.sh_mrp_ids = [(6, 0, mrp_orders.ids)]
                else:
                    rec.sh_mrp_ids = False

    """Fin du code acheté"""