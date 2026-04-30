from odoo import fields, models


class SubscriptionTag(models.Model):
    _name = 'subscription.tag'
    _description = 'Subscription Tag'
    _order = 'name'

    name = fields.Char(required=True, translate=True)
    color = fields.Integer(string='Color Index')
    active = fields.Boolean(default=True)
