from odoo import fields, models


class SubscriptionStage(models.Model):
    _name = 'subscription.stage'
    _description = 'Subscription Stage'
    _order = 'sequence, id'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    fold = fields.Boolean(
        string='Folded in Kanban',
        help='Fold this stage in the kanban view when there are no records in it.',
    )
    category = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('cancelled', 'Cancelled'),
        ('closed', 'Closed'),
    ], required=True, default='draft')
    description = fields.Text(translate=True)
    mail_template_id = fields.Many2one(
        'mail.template',
        string='Email Template',
        domain=[('model', '=', 'subscription.subscription')],
        help='Automatically send an email when a subscription reaches this stage.',
    )
