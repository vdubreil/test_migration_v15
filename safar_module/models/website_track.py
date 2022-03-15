# -*- coding: utf-8 -*-
from odoo import fields, models, api
from datetime import datetime
from odoo.http import request

class WebsiteTrack(models.Model):
    _inherit = 'website.track'


    def _track_visit_web_page(self,mypage=0, myurl="", myvisitor=0):
        vals = []
        vals = {
            'page_id': mypage,
            'url': myurl,
            'visitor_id': myvisitor,
            'visit_datetime': datetime.now(),
        }
        webtrack = request.env['website.track'].sudo()
        webtrack.create(vals)