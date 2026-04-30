from odoo import api, fields, models
from odoo.tools.translate import _


class SubscriptionRenewWizard(models.TransientModel):
    _name = 'subscription.renew.wizard'
    _description = 'Renew Subscriptions'

    subscription_ids = fields.Many2many(
        'subscription.subscription',
        string='Subscriptions',
    )
    new_date_end = fields.Date(string='New End Date', required=True)
    create_invoice = fields.Boolean(
        string='Generate Invoice',
        default=True,
    )
    note = fields.Text(string='Renewal Note')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get('active_ids') or self.env.context.get(
            'default_subscription_ids', []
        )
        if active_ids:
            res['subscription_ids'] = active_ids
        return res

    def action_renew(self):
        self.ensure_one()
        if not self.subscription_ids:
            return {'type': 'ir.actions.act_window_close'}

        invoices = self.env['account.move']
        for sub in self.subscription_ids:
            sub.write({'date_end': self.new_date_end})
            msg = _('Subscription renewed until %s.') % self.new_date_end
            if self.note:
                msg += f'\n{self.note}'
            sub.message_post(body=msg, message_type='notification')

            if self.create_invoice:
                invoice = sub._create_invoice()
                invoices |= invoice

        if invoices:
            invoices.action_post()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Renewed'),
                'message': _('%d subscription(s) renewed successfully.') % len(self.subscription_ids),
                'type': 'success',
                'sticky': False,
            },
        }
