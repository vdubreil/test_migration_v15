# -*- coding: utf-8 -*-
{
    'name': "safar_module",

    'summary': """
        Module de spécification pour l'entreprise Safar""",

    'description': """
        Module de spécification pour l'entreprise Safar
    """,

    'author': "JJB Conseil",
    'website': "",
    'license': 'LGPL-3',
    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.4',

    # any module necessary for this one to work correctly
    'depends': ['account', 'base', 'contacts', 'product', 'sale', 'mrp', 'stock', 'sale_stock', 'web', 'purchase',
                'hr', 'quality_control', 'mrp_workorder', 'delivery', 'account_batch_payment', 'website', 'documents', 'crm',
                'website_sale', 'helpdesk'],

    # 'qweb': [
    #     'static/src/xml/copy_paste_btn.xml',
    # ],
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/user_groups.xml',
        'data/backup_data.xml',
        'data/cron_customer_actif.xml',
        'data/cron_bascule_dossier_prod_of.xml',
        'data/cron_cancel_reservation_planificateur.xml',
        'data/cron_fermer_tache_operateur.xml',
        'views/account_journal.xml',
        'views/account_move.xml',
        'views/article.xml',
        'views/article_safar.xml',
        'views/article_search.xml',
        'views/article_categorie_pdr.xml',
        'views/article_marche.xml',
        'views/caract_gabarit_caracteristique.xml',
        'views/caract_gabarit_famille.xml',
        'views/caract_gabarit_ssfamille.xml',
        'views/caract_gabarit_valeur.xml',
        'views/choose_delivery_package.xml',
        'views/company.xml',
        'views/delai_fabrication.xml',
        'views/backup_view.xml',
        'views/facturation_importateur.xml',
        'views/famille_client.xml',
        'views/groupe_client.xml',
        'views/gabarit_lectra.xml',
        'views/helpdesk.xml',
        'views/hr_employee.xml',
        'views/image_simulateur.xml',
        'views/ligne_commande.xml',
        'views/mail_bounce.xml',
        'views/mail_activity.xml',
        'views/mail_message.xml',
        'views/mrp.bom.xml',
        'views/mrp_box.xml',
        'views/mrp_production.xml',
        'views/mrp.routing.workcenter.xml',
        'views/mrp_workcenter_productivity.xml',
        'views/mrp_workorder.xml',
        'views/note_template.xml',
        'views/partner.xml',
        'views/partner_origin.xml',
        'views/portal.xml',
        'views/portal_breadcrumbs.xml',
        'views/portal_document.xml',
        'views/portal_duplicate_so.xml',
        'views/portal_my_bls.xml',
        'views/portal_my_docs.xml',
        'views/portal_my_orders.xml',
        'views/portal_my_prices.xml',
        'views/portal_login.xml',
        'views/portal_footer.xml',
        'views/portal_promo.xml',
        'views/product_pricelist.xml',
        'views/product_pricelist_item.xml',
        'views/product_pricelist_item_tree_from_product.xml',
        'views/product_template_ecommerce.xml',
        'views/produit_client.xml',
        'views/purchase_order.xml',
        'views/quality_check.xml',
        'views/report.xml',
        'views/report_address_layout.xml',
        'views/report_delivery_document.xml',
        'views/report_internal_layout.xml',
        'views/report_invoice_document.xml',
        'views/report_invoice_document_address.xml',
        'views/report_label_etiquette.xml',
        'views/report_label_livraison.xml',
        'views/report_mrp_production.xml',
        'views/report_portal_saleorder.xml',
        'views/report_purchaseorder_document.xml',
        'views/report_saleorder_analysis.xml',
        'views/report_saleorder_document.xml',
        'views/report_external_layout_standard.xml',
        'views/sale_order.xml',
        'views/stock_picking.xml',
        'views/stock_quant_package.xml',
        'views/stock_valuation_layer.xml',
        'views/structure_juridique.xml',
        'views/univers_gabarit.xml',
        'views/vehicule.xml',
        'views/vehicule_finition.xml',
        'views/vehicule_gabarit.xml',
        'views/vehicule_generation.xml',
        'views/vehicule_marque.xml',
        'views/vehicule_modele.xml',
        'views/vehicule_serie.xml',
        'views/vehicule_univers.xml',
        'views/inventaire.xml',
        'views/website_product.xml',
        # 'views/mrp.routing.xml',
    ],
    'images': [
        'static/src/img/lavage_30.jpg',
        'static/src/img/lavage_main.jpg',
        'static/src/img/repassage.jpg',
        'static/src/img/repassage_no.jpg',
        'static/src/img/pressing.jpg',
        'static/src/img/blanchiment_no.jpg',
        'static/src/img/solvant_no.jpg',
        'static/src/img/lavelinge_no.jpg',
        'static/src/img/sechelinge.jpg',
    ],
    # 'js': [
    #     'static/src/js/clipboard.js'
    # ],

    # only loaded in demonstration mode
    'demo': [
    ],
}
