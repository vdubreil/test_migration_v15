# -*- coding: utf-8 -*-
from odoo import fields, models, api


class ProductTemplateAttributeValue(models.Model):
    _inherit = 'product.template.attribute.value'

    def write(self, values):
        record = super(ProductTemplateAttributeValue, self).write(values)

        self.product_tmpl_id.recalcule_list_price(self.product_tmpl_id.list_price)

        return record