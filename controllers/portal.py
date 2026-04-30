from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class SubscriptionPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'subscription_count' in counters:
            partner = request.env.user.partner_id
            subscription_count = request.env['subscription.subscription'].search_count([
                ('partner_id', 'child_of', [partner.commercial_partner_id.id]),
                ('stage_id.category', '=', 'in_progress'),
            ])
            values['subscription_count'] = subscription_count
        return values

    @http.route([
        '/my/subscriptions',
        '/my/subscriptions/page/<int:page>',
    ], type='http', auth='user', website=True)
    def portal_my_subscriptions(self, page=1, sortby=None, **kwargs):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id

        domain = [
            ('partner_id', 'child_of', [partner.commercial_partner_id.id]),
        ]
        sortings = {
            'date': {'label': 'Newest', 'order': 'date_start desc'},
            'name': {'label': 'Reference', 'order': 'name'},
            'stage': {'label': 'Stage', 'order': 'stage_id'},
        }
        order = sortings.get(sortby, sortings['date'])['order']

        subscription_count = request.env['subscription.subscription'].search_count(domain)
        pager = portal_pager(
            url='/my/subscriptions',
            total=subscription_count,
            page=page,
            step=self._items_per_page,
        )

        subscriptions = request.env['subscription.subscription'].search(
            domain,
            order=order,
            limit=self._items_per_page,
            offset=pager['offset'],
        )

        values.update({
            'subscriptions': subscriptions,
            'page_name': 'subscription',
            'pager': pager,
            'sortings': sortings,
            'sortby': sortby,
            'default_url': '/my/subscriptions',
        })
        return request.render(
            'odoo_subscription_manager.portal_my_subscriptions', values
        )

    @http.route(['/my/subscriptions/<int:subscription_id>'], type='http', auth='user', website=True)
    def portal_subscription_detail(self, subscription_id, **kwargs):
        subscription = request.env['subscription.subscription'].browse(subscription_id)
        if not subscription.exists():
            return request.redirect('/my/subscriptions')

        partner = request.env.user.partner_id
        if subscription.partner_id.commercial_partner_id != partner.commercial_partner_id:
            return request.redirect('/my/subscriptions')

        values = self._prepare_portal_layout_values()
        values.update({
            'subscription': subscription,
            'page_name': 'subscription',
        })
        return request.render(
            'odoo_subscription_manager.portal_subscription_detail', values
        )
