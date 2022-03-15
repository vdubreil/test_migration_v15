# -*- coding: utf-8 -*-
from odoo import fields, models, api
from datetime import datetime, timedelta

import logging

_logger = logging.getLogger(__name__)


class WebsiteVisitor(models.Model):
    _inherit = 'website.visitor'

    def _track_visit_web_visitor(self, mypage=0, myurl=""):
        visitor_sudo = self._get_visitor_from_request(force_create=True)

        if visitor_sudo:
            # on mémorise la page vue
            WebsiteTrack = self.env['website.track']
            WebsiteTrack._track_visit_web_page(mypage, myurl, visitor_sudo.id)

            # on met à jour la visite
            try:
                with self.env.cr.savepoint():
                    query_lock = "SELECT * FROM website_visitor where id = %s FOR NO KEY UPDATE NOWAIT"
                    self.env.cr.execute(query_lock, (visitor_sudo.id,), log_exceptions=False)

                    date_now = datetime.now()

                    query = "UPDATE website_visitor SET "
                    if visitor_sudo.last_connection_datetime < (date_now - timedelta(hours=8)):
                        query += "visit_count = visit_count + 1,"
                    query += """
                        active = True,
                        last_connection_datetime = %s
                        WHERE id = %s
                    """
                    self.env.cr.execute(query, (date_now, visitor_sudo.id), log_exceptions=True)

            except Exception:
                pass

    # @api.onchange('last_connection_datetime')
    @api.depends('website_track_ids.page_id')
    def _compute_last_visited_page_id(self):
        results = self.env['website.track'].read_group([('visitor_id', 'in', self.ids)],
                                                       ['visitor_id', 'page_id', 'visit_datetime:max'],
                                                       ['visitor_id', 'page_id'], lazy=False)
        mapped_data = {result['visitor_id'][0]: result['page_id'][0] for result in results if result['page_id']}
        for visitor in self:
            visitor.last_visited_page_id = mapped_data.get(visitor.id, False)

        return super(WebsiteVisitor, self)._compute_last_visited_page_id()