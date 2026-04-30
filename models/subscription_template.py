from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SubscriptionTemplate(models.Model):
    _name = 'subscription.template'
    _description = 'Subscription Template'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(required=True, translate=True, tracking=True)
    active = fields.Boolean(default=True)
    code = fields.Char(
        string='Internal Reference',
        copy=False,
        readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('subscription.template'),
    )
    description = fields.Html(translate=True)
    billing_cycle = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly (3 months)'),
        ('biannual', 'Bi-Annual (6 months)'),
        ('annual', 'Annual'),
        ('custom', 'Custom'),
    ], required=True, default='monthly', tracking=True)
    custom_cycle_days = fields.Integer(
        string='Custom Cycle (Days)',
        help='Number of days between renewals when billing cycle is Custom.',
    )
    duration_months = fields.Integer(
        string='Initial Duration (Months)',
        default=12,
        help='Default contract duration in months. 0 = indefinite.',
    )
    auto_renew = fields.Boolean(
        string='Auto-Renew',
        default=True,
        help='Automatically renew subscriptions before expiration.',
        tracking=True,
    )
    renewal_lead_days = fields.Integer(
        string='Renewal Lead Time (Days)',
        default=15,
        help='How many days before expiration to trigger automatic renewal.',
    )
    product_ids = fields.Many2many(
        'product.product',
        'subscription_template_product_rel',
        'template_id', 'product_id',
        string='Default Products',
        domain=[('type', 'in', ['service', 'consu'])],
    )
    invoice_policy = fields.Selection([
        ('advance', 'Invoice in Advance'),
        ('arrears', 'Invoice in Arrears'),
    ], default='advance', required=True)
    payment_term_id = fields.Many2one(
        'account.payment.term',
        string='Payment Terms',
    )
    pricelist_id = fields.Many2one(
        'product.pricelist',
        string='Pricelist',
    )
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True,
    )
    tag_ids = fields.Many2many('subscription.tag', string='Tags')
    note = fields.Html(string='Terms and Conditions', translate=True)

    # Stats
    subscription_count = fields.Integer(
        compute='_compute_subscription_count',
        string='Subscriptions',
    )
    active_subscription_count = fields.Integer(
        compute='_compute_subscription_count',
        string='Active Subscriptions',
    )

    @api.depends('billing_cycle', 'custom_cycle_days')
    def _compute_subscription_count(self):
        for template in self:
            subs = self.env['subscription.subscription'].search([
                ('template_id', '=', template.id),
            ])
            template.subscription_count = len(subs)
            template.active_subscription_count = len(
                subs.filtered(lambda s: s.stage_id.category == 'in_progress')
            )

    @api.constrains('custom_cycle_days', 'billing_cycle')
    def _check_custom_cycle(self):
        for rec in self:
            if rec.billing_cycle == 'custom' and rec.custom_cycle_days <= 0:
                raise ValidationError(
                    'Custom cycle days must be greater than 0.'
                )

    def get_cycle_days(self):
        self.ensure_one()
        mapping = {
            'monthly': 30,
            'quarterly': 90,
            'biannual': 180,
            'annual': 365,
            'custom': self.custom_cycle_days,
        }
        return mapping.get(self.billing_cycle, 30)

    def action_view_subscriptions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Subscriptions',
            'res_model': 'subscription.subscription',
            'view_mode': 'list,kanban,form',
            'domain': [('template_id', '=', self.id)],
            'context': {'default_template_id': self.id},
        }
