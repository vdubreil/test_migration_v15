# -*- coding: utf-8 -*-
import binascii
from datetime import date

from odoo import fields, models, http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers.mail import _message_post_helper
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager, get_records_pager

import logging

_logger = logging.getLogger(__name__)


class CustomerPortal(CustomerPortal):
    # ---------------------------------------------------------------------
    # Comptage des éléments listés
    def _prepare_home_portal_values(self):
        values = super(CustomerPortal, self)._prepare_home_portal_values()
        partner = request.env.user.partner_id

        StockPicking = request.env['stock.picking']
        picking_count = StockPicking.search_count([
            ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('state', 'in', ['assigned', 'done'])
        ]) if StockPicking.check_access_rights('read', raise_exception=False) else 0

        #         domain_tag_ids = partner.s_portail_tag_autorisees.s_tag_ids
        #         Document = request.env['documents.document']
        #         document_count = Document.search_count([
        #             ('folder_id', '=', 6), # 6 = id du workspace Portail
        #             '|',('tag_ids', '=', False), ('tag_ids', 'in', [g.id for g in domain_tag_ids]),
        #         ]) if Document.check_access_rights('read', raise_exception=False) else 0

        values.update({
            'picking_count': picking_count,
            #             'document_count': document_count,
        })
        return values

    # ---------------------------------------------------------------------
    # POUR DUPLIQUER UNE CDE
    @http.route(['/my/orders/<int:order_id>/duplicate'], type='http', auth="public", methods=['POST'], website=True)
    def duplicate(self, order_id, access_token=None, **post):
        try:
            order_sudo = self._document_check_access('sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        # Récup des infos saisies dans le formulaire
        message = post.get('duplicate_message')
        ref_clt = post.get('ref_order_client')
        # Récup du channel portail paramétré dans la fiche société
        channel_portail = False
        company = request.env['res.company'].search([('id', '=', order_sudo.company_id.id)])
        if company:
            if company.s_global_channel_portail:
                channel_portail = company.s_global_channel_portail.id

        # Dictionnaire de valeur pour créer la sale.order
        val = []
        val = {
            'client_order_ref': ref_clt if ref_clt else '',
            'global_channel_id': channel_portail,
            'user_id': False,
        }

        if message:
            # il y a un message donc c'est pour un devis
            msg = "Devis créé par le client à partir de sa commande "
            msg += "<a href=# data-oe-model=sale.order data-oe-id=%d>%s</a>" % (
            order_sudo.id, order_sudo.name) + '<br/>'
            msg += "Souhaits du client pour cette quotation : " + '<br/>' + str(message)
            val['state'] = 'draft'
            order = order_sudo.action_duplicate(val)
            if order:
                _logger.critical("ORDER=" + str(order.id))
                query_string = '&message=quotation_ok'
                order.message_post(body=msg)
                self.abonner_follower_adv(order)
            else:
                query_string = '&message=quotation_ko'

            return request.redirect(order_sudo.get_portal_url(query_string=query_string))
        else:
            # pas de message donc c'est pour une duplication à l'identique de la cde
            val['state'] = 'sent'
            order = order_sudo.action_duplicate(val)
            if order:
                query_string = '&message=duplicate_ok'
                #                 msg = 'Commande passée par le client à partir de la commande ' + str(order_sudo.name)
                msg = 'Commande passée par le client à partir de la commande '
                msg += "<a href=# data-oe-model=sale.order data-oe-id=%d>%s</a>" % (order_sudo.id, order_sudo.name)

                order.message_post(body=msg)
                self.abonner_follower_adv(order)
                return request.redirect(order.get_portal_url(query_string=query_string))
            else:
                query_string = '&message=duplicate_ko'
                return request.redirect('/my')

    def abonner_follower_adv(self, myorder):
        # On cherche le res.groups "Notifier si commande portail"
        Res_Groups = request.env['res.groups'].sudo()
        Grp_Notif = Res_Groups.search([('id', '=', 112)])  # 112 est l'id du res.groups "Notifier si commande portail"
        # Table des abonnés pour recevoir les notifications
        Follower = request.env["mail.followers"]
        # on définit les dict pour envoyer à la création des followers
        liste_id = []
        liste_id.append(myorder.id)
        liste_user = []
        for us in Grp_Notif.users:
            if us.id not in liste_user:
                liste_user.append(us.partner_id.id)
        Follower._insert_followers("sale.order", liste_id, liste_user, None, None, None)

    # ---------------------------------------------------------------------
    # POUR CONSULTER LA LISTE DES REPS/DOCUMENTS
    @http.route(['/my/docs', '/my/docs/page/<int:page>', '/my/docs/folder/<int:fold>'], type='http', auth="user",
                website=True)
    def portal_my_docs(self, page=1, fold=6, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        User = request.env.user
        Document = request.env['documents.document']
        Folder = request.env['documents.folder']
        Group = request.env['res.groups'].sudo()

        # Tracking
        self.tracking(57)

        # On vérifie que le folder demandé est bien accessible par l'utilisateur
        current_fold = False
        if fold:
            grp_portal = Group.search([('id', '=', '9')], limit=1)  # id = 9 => groupe "Type utilisateur / Portail"
            if grp_portal:
                current_fold = Folder.search(
                    ['&', ('id', '=', fold), ('read_group_ids', 'in', [g.id for g in grp_portal])], limit=1)
                if not current_fold:
                    return request.redirect('/my')
                    # On cherche l'arborescence montante des répertoires pour le breadcrumbs
                list_folder = []
                arbo_fold = current_fold
                while arbo_fold:
                    list_folder.insert(0, str(arbo_fold.id) + '|' + str(arbo_fold.name))
                    # on boucle en remontant vers chaque répertoire parent
                    arbo_fold = Folder.search(['&', ('id', '=', arbo_fold.parent_folder_id.id),
                                               ('read_group_ids', 'in', [g.id for g in grp_portal])], limit=1)
                _logger.critical("ARBO_NAME = " + str(list_folder))

        domain_tag_ids = partner.s_portail_tag_autorisees.s_tag_ids
        #         _logger.critical("FOLDER_ID="+str(domain_tag_ids))
        domain_doc = [
            #             ('partner_id', 'in', [partner.commercial_partner_id.id])
            ('folder_id', 'in', [fold]),
            '|', ('tag_ids', '=', False), ('tag_ids', 'in', [g.id for g in domain_tag_ids]),
        ]
        domain_rep = [
            ('parent_folder_id', 'in', [fold]),
            ('read_group_ids', 'in', [g.id for g in User.groups_id])
        ]

        searchbar_sortings = {
            'name': {'label': _('Nom'), 'order': 'name'},
        }
        # default sortby order
        if not sortby:
            sortby = 'name'
        sort_order = searchbar_sortings[sortby]['order']

        archive_groups = self._get_archive_groups('documents.document', domain_doc) if values.get('my_details') else []
        if date_begin and date_end:
            domain_doc += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # count for pager
        doc_count = Document.search_count(domain_doc)
        rep_count = Folder.search_count(domain_rep)

        doc_count += rep_count

        # pager
        pager = portal_pager(
            url="/my/docs",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=doc_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        mydocs = Document.search(domain_doc, order=sort_order, limit=self._items_per_page, offset=pager['offset'])
        myreps = Folder.search(domain_rep, order=sort_order, limit=self._items_per_page, offset=pager['offset'])

        #         request.session['my_docs_history'] = mydocs.ids[:100]
        #         request.session['my_reps_history'] = myreps.ids[:100]

        values.update({
            'date': date_begin,
            'mydocs': mydocs.sudo(),
            'myreps': myreps.sudo(),
            'page_name': 'my_docs',
            'pager': pager,
            'archive_groups': archive_groups,
            'default_url': '/my/docs',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'fold': Folder.id,
            'arbo_list_folder': list_folder,
        })
        #         _logger.critical("DOCS1="+values['mydocs'])
        return request.render("safar_module.s_portal_my_docs", values)

    # ---------------------------------------------------------------------
    # LORS D'UNE RECHERCHE D'UN ELEMENT DE LA CDE
    # Reprise de la fonction Odoo d'origine pour afficher les cdes avec ajout d'une fonction de recherche pour enrichir le domaine de recherche
    @http.route(['/my/orders/search'], type='http', auth="public", methods=['POST'], website=True)
    def search_order(self, page=1, date_begin=None, date_end=None, sortby=None, **post):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        SaleOrder = request.env['sale.order']
        SaleOrderLine = request.env['sale.order.line']

        domain = [
            ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('state', 'in', ['sale', 'done']),
        ]

        # Recherche d'un élément parmis les lignes
        val_recherche = post.get('order_search')
        if val_recherche:
            all_orders_clt = SaleOrder.search(domain)  # Liste de toutes les commandes du client
            if all_orders_clt:
                domain_line = [
                    ('order_id', 'in', [g.id for g in all_orders_clt]),
                    '|', ('s_configuration', 'ilike', str(val_recherche)), ('name', 'ilike', str(val_recherche))
                ]
                _logger.critical("DOMAIN=" + str(domain_line))
                order_line = SaleOrderLine.search(domain_line)
                if order_line:
                    _logger.critical("ORDER_LINE=" + str(order_line))
                    liste_order = []
                    for so in order_line:
                        if so.order_id not in liste_order:
                            liste_order.append(so.order_id)
                    _logger.critical("LIST_ORDER=" + str(liste_order))
                    domain += [('id', 'in', [g.id for g in liste_order])]
                else:
                    domain += [('id', '=',
                                -1)]  # domaine fictif pour retourner une liste vide que l'utilisateur voit bien que sa recherche n'a rien donnée

        searchbar_sortings = {
            'date': {'label': _('Order Date'), 'order': 'date_order desc'},
            'name': {'label': _('Reference'), 'order': 'name'},
            'stage': {'label': _('Stage'), 'order': 'state'},
        }
        # default sortby order
        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['order']

        archive_groups = self._get_archive_groups('sale.order', domain) if values.get('my_details') else []
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # count for pager
        order_count = SaleOrder.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/orders",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=order_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        orders = SaleOrder.search(domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_orders_history'] = orders.ids[:100]

        values.update({
            'date': date_begin,
            'orders': orders.sudo(),
            'page_name': 'order',
            'pager': pager,
            'archive_groups': archive_groups,
            'default_url': '/my/orders',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        return request.render("sale.portal_my_orders", values)

    # ---------------------------------------------------------------------
    # LISTER LES BL
    @http.route(['/my/bls', '/my/bls/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_bls(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        _logger.critical("LISTER_BL")
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        StockPicking = request.env['stock.picking']

        # Tracking
        self.tracking(56)

        domain = [
            ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('state', 'in', ['assigned', 'done'])
        ]

        searchbar_sortings = {
            'date': {'label': _('Date de livraison'), 'order': 'date_done desc'},
            'name': {'label': _('Reference'), 'order': 'name'},
            'stage': {'label': _('Stage'), 'order': 'state'},
        }
        # default sortby bl
        if not sortby:
            sortby = 'date'
        sort_bl = searchbar_sortings[sortby]['order']

        archive_groups = self._get_archive_groups('stock.picking', domain) if values.get('my_details') else []
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # count for pager
        picking_count = StockPicking.search_count(domain)
        _logger.critical("NB_BL=" + str(picking_count))
        # pager
        pager = portal_pager(
            url="/my/bls",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=picking_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        bls = StockPicking.search(domain, order=sort_bl, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_bls_history'] = bls.ids[:100]

        values.update({
            'date': date_begin,
            'mybls': bls.sudo(),
            'page_name': 'my_bls',
            'pager': pager,
            'archive_groups': archive_groups,
            'default_url': '/my/bls',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        return request.render("safar_module.s_portal_my_bls", values)

    # ---------------------------------------------------------------------
    # LISTER LES CDES
    @http.route(['/my/orders'], type='http', auth="user", website=True)
    def portal_my_orders(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        self.tracking(55)

        return super(CustomerPortal, self).portal_my_orders(page, date_begin, date_end, sortby, **kw)

    # ---------------------------------------------------------------------
    # LISTER LES ACHATS
    @http.route(['/my/purchase'], type='http', auth="user", website=True)
    def portal_my_purchase_orders(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        self.tracking(58)

        return super(CustomerPortal, self).portal_my_purchase_orders(page, date_begin, date_end, sortby, **kw)

    # ---------------------------------------------------------------------
    # LISTER LES FACTURES
    @http.route(['/my/invoices'], type='http', auth="user", website=True)
    def portal_my_invoices(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        self.tracking(59)

        return super(CustomerPortal, self).portal_my_invoices(page, date_begin, date_end, sortby, **kw)

    # ---------------------------------------------------------------------
    # LISTER LES TICKETS
    @http.route(['/my/tickets'], type='http', auth="user", website=True)
    def my_helpdesk_tickets(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        self.tracking(60)

        return super(CustomerPortal, self).my_helpdesk_tickets(page, date_begin, date_end, sortby, **kw)

    # ---------------------------------------------------------------------
    # LISTER LES DEVIS
    @http.route(['/my/quotes'], type='http', auth="user", website=True)
    def portal_my_quotes(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        self.tracking(61)

        return super(CustomerPortal, self).portal_my_quotes(page, date_begin, date_end, sortby, **kw)

    # ---------------------------------------------------------------------
    # Mémoriser le tracking
    def tracking(self, page_track):
        myurl = request.httprequest.url
        WebsiteVisitor = request.env['website.visitor']
        WebsiteVisitor._track_visit_web_visitor(page_track, myurl)