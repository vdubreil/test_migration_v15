# -*- coding: utf-8 -*-
from odoo import fields, models, api


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    s_tx_remise_liste = fields.Float(string="Remise sur Prix de Vente Catalogue (%)")
    s_faire_recalcul_prix = fields.Boolean(string="Recalculer les prix")

    # def get_products_refclient(self, products, quantities, partners, date=False, uom_id=False):
    #     """ For a given pricelist, return ref client for products
    #     Returns: dict{product_id: product price}, in the given pricelist """
    #     self.ensure_one()
    #     return {
    #         product_id: res_tuple[0]
    #         for product_id, res_tuple in self._compute_price_rule(
    #             list(zip(products, quantities, partners)),
    #             date=date,
    #             uom_id=uom_id
    #         ).items()
    #     }

    def call_safar_calculer_prix(self):
        # Pour la fonction ROUND, on ajoute 0.0001 à la valeur pour palier le problème d'arrondi à l'entier pair le plus proche
        # exemple : 82.5 donne 82 en python au lieu de 83
        # En ajoutant 0.0001, on obtient 82.5001 ce qui donne bien 83
        if self.s_faire_recalcul_prix:
            for item in self.with_context().item_ids:
                if item.product_id:
                    # variante
                    item.fixed_price = round((item.product_id.lst_price * (
                                1 - (self.s_tx_remise_liste / 100) - (item.s_tx_remise_liste_item / 100))) + 0.0001, 0)
                else:
                    if item.product_tmpl_id.list_price:
                        # article
                        item.fixed_price = round((item.product_tmpl_id.list_price * (
                                    1 - (self.s_tx_remise_liste / 100) - (item.s_tx_remise_liste_item / 100))) + 0.0001, 0)