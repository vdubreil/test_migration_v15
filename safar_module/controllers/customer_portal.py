# -*- coding: utf-8 -*-
import binascii
from datetime import date

from odoo import fields, models, http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers.mail import _message_post_helper
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager, get_records_pager
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.osv import expression

import logging
_logger = logging.getLogger(__name__)


class CustomerPortal(CustomerPortal):
    # ---------------------------------------------------------------------
    # Comptage des éléments listés
    def _prepare_home_portal_values(self):
        values = super(CustomerPortal, self)._prepare_home_portal_values()
        partner = request.env.user.partner_id

        # comptage des BL (attention le domain doit être le même que dans la fonction de routing http)
        StockPicking = request.env['stock.picking']
        picking_count = StockPicking.search_count([
            ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('state', 'in', ['assigned', 'done'])
        ]) if StockPicking.check_access_rights('read', raise_exception=False) else 0

        # comptage des documents
        #         domain_tag_ids = partner.s_portail_tag_autorisees.s_tag_ids
        #         Document = request.env['documents.document']
        #         document_count = Document.search_count([
        #             ('folder_id', '=', 6), # 6 = id du workspace Portail
        #             '|',('tag_ids', '=', False), ('tag_ids', 'in', [g.id for g in domain_tag_ids]),
        #         ]) if Document.check_access_rights('read', raise_exception=False) else 0

        # comptage des tarifs (attention le domain doit être le même que dans la fonction de routing http)
        ProductPricelistItem = request.env['product.pricelist.item'].sudo()
        domain = []
        if partner.parent_id:  # le connecté a un parent
            _logger.critical("le connecté à un parent=" + str(partner.parent_id.id))
            if partner.parent_id.s_id_client_facture:  # le parent du connecté à un facturé
                _logger.critical("le parent du connecté à un facturé=" + str(partner.parent_id.s_id_client_facture.id))
                if partner.parent_id.s_id_client_facture.property_product_pricelist:
                    domain = [
                        ('pricelist_id', 'in', [partner.parent_id.s_id_client_facture.property_product_pricelist.id]),
                    ]
                    _logger.critical(
                        "domain=" + str(partner.parent_id.s_id_client_facture.property_product_pricelist.id))
            else:  # le parent du connecté n'a pas de facturé
                if partner.parent_id.property_product_pricelist:
                    domain = [
                        ('pricelist_id', 'in', [partner.parent_id.property_product_pricelist.id]),
                    ]
        else:  # le connecté n'a pas de parent
            if partner.s_id_client_facture:  # le connecté à un facturé
                if partner.s_id_client_facture.property_product_pricelist:
                    domain = [
                        ('pricelist_id', 'in', [partner.s_id_client_facture.property_product_pricelist.id]),
                    ]

        if domain:
            price_count = ProductPricelistItem.search_count(domain)
        else:
            price_count = 0

        values.update({
            'picking_count': picking_count,
            'price_count': price_count,
            #             'document_count': document_count,
        })
        return values

    # ---------------------------------------------------------------------
    # Renvoyer le partner correspondant au num de tél transmis
    @http.route(['/phone_number=<string:phone>'], type='http', auth="user", website=True)
    def get_partner_of_phone(self, phone='', **kw):
        _logger.critical("APPEL RECU : " + str(phone) + "/" + str(phone[-9:]))
        Partner = request.env['res.partner'].sudo()
        partners_called = Partner.search(
            ['|', ('s_phone_num', 'ilike', phone[-9:]), ('s_mobile_num', 'like', phone[-9:])])
        if partners_called:
            for partner_called in partners_called:
                _logger.critical("PARTNER CALLED = " + str(partner_called.id))
                if partner_called.parent_id:
                    return request.redirect('/web#id=' + str(partner_called.parent_id.id) + '&action=663&model=res.partner&view_type=form&cids=1&menu_id=436')
                else:
                    return request.redirect('/web#id=' + str(partner_called.id) + '&action=663&model=res.partner&view_type=form&cids=1&menu_id=436')

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
        Partners = request.env['res.partner'].sudo()

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
        partner_parent = Partners.search([('id', '=', partner.parent_id.id)]).sudo()
        if partner_parent:
            if partner_parent.s_portail_tag_autorisees.s_tag_ids:
                domain_tag_ids += partner_parent.s_portail_tag_autorisees.s_tag_ids

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
    # LISTER LES TARIFS
    @http.route(['/my/prices', '/my/prices/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_prices(self, page=1, date_begin=None, date_end=None, sortby=None,
                         **kw):  # , search=False  , 'my/prices/search'
        _logger.critical("LISTER_PRICE")
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        ProductPricelistItem = request.env['product.pricelist.item'].sudo()

        # Tracking
        self.tracking(65)

        # Le domain doit être en phase avec le domain qui se trouve dans la fonction _prepare_portal_layout_values() située en haut !!!!
        domain = []
        if partner.parent_id:  # le connecté a un parent
            _logger.critical("le connecté à un parent=" + str(partner.parent_id.id))
            if partner.parent_id.s_id_client_facture:  # le parent du connecté à un facturé
                _logger.critical(
                    "le parent du connecté à un facturé=" + str(partner.parent_id.s_id_client_facture.id))
                if partner.parent_id.s_id_client_facture.property_product_pricelist:
                    domain = [
                        ('pricelist_id', 'in',
                         [partner.parent_id.s_id_client_facture.property_product_pricelist.id]),
                    ]
                    _logger.critical(
                        "domain=" + str(partner.parent_id.s_id_client_facture.property_product_pricelist.id))
            else:  # le parent du connecté n'a pas de facturé
                if partner.parent_id.property_product_pricelist:
                    domain = [
                        ('pricelist_id', 'in', [partner.parent_id.property_product_pricelist.id]),
                    ]
        else:  # le connecté n'a pas de parent
            if partner.s_id_client_facture:  # le connecté à un facturé
                if partner.s_id_client_facture.property_product_pricelist:
                    domain = [
                        ('pricelist_id', 'in', [partner.s_id_client_facture.property_product_pricelist.id]),
                    ]
        if not domain:
            domain = [
                ('pricelist_id', 'in', [0]),
            ]

        #         if search:
        #             val_recherche = post.get('price_search')
        #             if val_recherche:
        #                 domain += [
        #                     ('s_ref_prdt_client', '=', 's_ref_prdt_client')
        #                 ]

        searchbar_sortings = {
            'name': {'label': _('Libellé Client'), 'order': 's_lib_prdt_client'},
            'ref': {'label': _('Reference'), 'order': 's_ref_prdt_client'},
        }
        # default sortby price
        if not sortby:
            sortby = 'name'
        sort_price = searchbar_sortings[sortby]['order']

        archive_groups = self._get_archive_groups('product.pricelist.item', domain) if values.get(
            'my_details') else []
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # count for pager
        price_count = ProductPricelistItem.search_count(domain)
        _logger.critical("NB_Price=" + str(price_count))
        # pager
        pager = portal_pager(
            url="/my/prices",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=price_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        prices = ProductPricelistItem.search(domain, order=sort_price, limit=self._items_per_page,
                                             offset=pager['offset'])
        request.session['my_prices_history'] = prices.ids[:100]

        values.update({
            'date': date_begin,
            'myprices': prices.sudo(),
            'page_name': 'my_prices',
            'pager': pager,
            'archive_groups': archive_groups,
            'default_url': '/my/prices',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'count_price': price_count,
        })
        return request.render("safar_module.s_portal_my_prices", values)

    # ---------------------------------------------------------------------
    # RECHERCHER LES TARIFS
    @http.route(['/my/prices/search'], type='http', auth="public", methods=['POST'], website=True)
    def search_price(self, page=1, date_begin=None, date_end=None, sortby=None, **post):
        _logger.critical("SEARCH_PRICE")
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        ProductPricelistItem = request.env['product.pricelist.item'].sudo()

        # Tracking
        self.tracking(65)

        # Le domain doit être en phase avec le domain qui se trouve dans la fonction _prepare_portal_layout_values() située en haut !!!!
        domain = []
        if partner.parent_id:  # le connecté a un parent
            _logger.critical("le connecté à un parent=" + str(partner.parent_id.id))
            if partner.parent_id.s_id_client_facture:  # le parent du connecté à un facturé
                _logger.critical(
                    "le parent du connecté à un facturé=" + str(partner.parent_id.s_id_client_facture.id))
                if partner.parent_id.s_id_client_facture.property_product_pricelist:
                    domain = [
                        ('pricelist_id', 'in',
                         [partner.parent_id.s_id_client_facture.property_product_pricelist.id]),
                    ]
                    _logger.critical(
                        "domain=" + str(partner.parent_id.s_id_client_facture.property_product_pricelist.id))
            else:  # le parent du connecté n'a pas de facturé
                if partner.parent_id.property_product_pricelist:
                    domain = [
                        ('pricelist_id', 'in', [partner.parent_id.property_product_pricelist.id]),
                    ]
        else:  # le connecté n'a pas de parent
            if partner.s_id_client_facture:  # le connecté à un facturé
                if partner.s_id_client_facture.property_product_pricelist:
                    domain = [
                        ('pricelist_id', 'in', [partner.s_id_client_facture.property_product_pricelist.id]),
                    ]
        if not domain:
            domain = [
                ('pricelist_id', 'in', [0]),
            ]

        val_recherche = post.get('price_search')
        if val_recherche:
            domain += [
                '|', ('s_ref_prdt_client', 'ilike', str(val_recherche)),
                '|', ('s_lib_prdt_client', 'ilike', str(val_recherche)),
                '|', ('product_tmpl_id.name', 'ilike', str(val_recherche)),
                ('product_tmpl_id.s_modele_associe', 'ilike', str(val_recherche)),
            ]

        searchbar_sortings = {
            'name': {'label': _('Libellé Client'), 'order': 's_lib_prdt_client'},
            'ref': {'label': _('Reference'), 'order': 's_ref_prdt_client'},
        }
        # default sortby price
        if not sortby:
            sortby = 'name'
        sort_price = searchbar_sortings[sortby]['order']

        archive_groups = self._get_archive_groups('product.pricelist.item', domain) if values.get(
            'my_details') else []
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # count for pager
        price_count = ProductPricelistItem.search_count(domain)
        _logger.critical("NB_Price=" + str(price_count))
        # pager
        pager = portal_pager(
            url="/my/prices",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=price_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        prices = ProductPricelistItem.search(domain, order=sort_price, limit=self._items_per_page,
                                             offset=pager['offset'])
        request.session['my_prices_history'] = prices.ids[:100]

        values.update({
            'date': date_begin,
            'myprices': prices.sudo(),
            'page_name': 'my_prices',
            'pager': pager,
            'archive_groups': archive_groups,
            'default_url': '/my/prices',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'count_price': price_count,
        })
        return request.render("safar_module.s_portal_my_prices", values)

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




class WebsiteSale(WebsiteSale):

    # ---------------------------------------------------------------------
    @http.route('/shop/products/autocomplete', type='json', auth='public', website=True)
    def products_autocomplete(self, term, options={}, **kwargs):

        res = super(WebsiteSale, self).products_autocomplete(term, options, **kwargs)
        # _logger.critical("RES_AVT="+str(res))
        if res:
            if 'products' in res:
                ProductTemplate = request.env['product.template']
                list_prdt = res['products']
                list_new_prdt = []
                for dict_prdt in list_prdt:
                    if dict_prdt['id']:
                        prdt = ProductTemplate.search([('id', '=', dict_prdt['id'])])
                        if prdt:
                            if prdt.s_lib_ecommerce:
                                dict_prdt['name'] = prdt.s_lib_ecommerce
                    list_new_prdt.append(dict_prdt)
                res['products'] = list_new_prdt
        # _logger.critical("RES_APR="+str(res))
        return res

    # ---------------------------------------------------------------------
    def _get_search_domain(self, search, category, attrib_values, search_in_description=True):
        domains = [request.website.sale_product_domain()]
        if search:
            for srch in search.split(" "):
                subdomains = [
                    [('name', 'ilike', srch)],
                    [('s_lib_ecommerce', 'ilike', srch)],
                    [('product_variant_ids.default_code', 'ilike', srch)]
                ]
                _logger.critical("DOMAIN=" + str(subdomains))
                if search_in_description:
                    subdomains.append([('description', 'ilike', srch)])
                    subdomains.append([('description_sale', 'ilike', srch)])
                domains.append(expression.OR(subdomains))

        if category:
            domains.append([('public_categ_ids', 'child_of', int(category))])

        if attrib_values:
            attrib = None
            ids = []
            for value in attrib_values:
                if not attrib:
                    attrib = value[0]
                    ids.append(value[1])
                elif value[0] == attrib:
                    ids.append(value[1])
                else:
                    domains.append([('attribute_line_ids.value_ids', 'in', ids)])
                    attrib = value[0]
                    ids = [value[1]]
            if attrib:
                domains.append([('attribute_line_ids.value_ids', 'in', ids)])

        return expression.AND(domains)