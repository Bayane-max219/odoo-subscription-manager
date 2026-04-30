from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    subscription_ids = fields.One2many(
        'subscription.subscription',
        'partner_id',
        string='Subscriptions',
    )
    subscription_count = fields.Integer(
        compute='_compute_subscription_count',
        string='Subscriptions',
    )
    active_subscription_count = fields.Integer(
        compute='_compute_subscription_count',
        string='Active Subscriptions',
    )

    @api.depends('subscription_ids', 'subscription_ids.stage_id')
    def _compute_subscription_count(self):
        for partner in self:
            partner.subscription_count = len(partner.subscription_ids)
            partner.active_subscription_count = len(
                partner.subscription_ids.filtered(
                    lambda s: s.stage_id.category == 'in_progress'
                )
            )

    def action_view_subscriptions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Subscriptions',
            'res_model': 'subscription.subscription',
            'view_mode': 'list,kanban,form',
            'domain': [('partner_id', 'in', self.ids)],
            'context': {'default_partner_id': self.id},
        }
