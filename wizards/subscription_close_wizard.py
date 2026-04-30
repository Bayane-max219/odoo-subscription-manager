from odoo import api, fields, models
from odoo.tools.translate import _


class SubscriptionCloseWizard(models.TransientModel):
    _name = 'subscription.close.wizard'
    _description = 'Close Subscriptions'

    subscription_ids = fields.Many2many(
        'subscription.subscription',
        string='Subscriptions',
    )
    close_reason = fields.Selection([
        ('customer_request', 'Customer Request'),
        ('non_payment', 'Non Payment'),
        ('end_of_contract', 'End of Contract'),
        ('upgrade', 'Upgraded to Higher Plan'),
        ('other', 'Other'),
    ], required=True, default='end_of_contract')
    close_date = fields.Date(
        string='Close Date',
        required=True,
        default=fields.Date.today,
    )
    note = fields.Text(string='Additional Notes')
    send_confirmation = fields.Boolean(
        string='Send Confirmation Email',
        default=True,
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get('active_ids') or self.env.context.get(
            'default_subscription_ids', []
        )
        if active_ids:
            res['subscription_ids'] = active_ids
        return res

    def action_close(self):
        self.ensure_one()
        closed_stage = self.env['subscription.stage'].search(
            [('category', '=', 'closed')], limit=1, order='sequence asc'
        )
        template = self.env.ref(
            'odoo_subscription_manager.mail_template_subscription_closed',
            raise_if_not_found=False,
        )
        reason_label = dict(self._fields['close_reason'].selection).get(self.close_reason, '')

        for sub in self.subscription_ids:
            vals = {
                'close_date': self.close_date,
                'close_reason': f'{reason_label}\n{self.note or ""}',
            }
            if closed_stage:
                vals['stage_id'] = closed_stage.id
            sub.write(vals)
            sub.message_post(
                body=_('Subscription closed. Reason: %s') % reason_label,
                message_type='notification',
            )
            if self.send_confirmation and template:
                template.send_mail(sub.id, force_send=True)

        return {'type': 'ir.actions.act_window_close'}
