from odoo import api, fields, models


class SubscriptionLine(models.Model):
    _name = 'subscription.line'
    _description = 'Subscription Line'
    _order = 'sequence, id'

    subscription_id = fields.Many2one(
        'subscription.subscription',
        required=True,
        ondelete='cascade',
        index=True,
    )
    sequence = fields.Integer(default=10)
    product_id = fields.Many2one(
        'product.product',
        required=True,
        domain=[('type', 'in', ['service', 'consu'])],
        ondelete='restrict',
    )
    name = fields.Text(
        string='Description',
        compute='_compute_name',
        store=True,
        readonly=False,
    )
    quantity = fields.Float(default=1.0, digits='Product Unit of Measure')
    uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        related='product_id.uom_id',
        store=True,
    )
    price_unit = fields.Float(
        string='Unit Price',
        digits='Product Price',
        compute='_compute_price_unit',
        store=True,
        readonly=False,
    )
    discount = fields.Float(string='Discount (%)', digits='Discount')
    tax_ids = fields.Many2many(
        'account.tax',
        string='Taxes',
        compute='_compute_tax_ids',
        store=True,
        readonly=False,
    )
    price_subtotal = fields.Monetary(
        compute='_compute_price_subtotal',
        store=True,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        related='subscription_id.currency_id',
        store=True,
    )
    company_id = fields.Many2one(
        related='subscription_id.company_id',
        store=True,
    )

    @api.depends('product_id')
    def _compute_name(self):
        for line in self:
            if line.product_id:
                line.name = line.product_id.get_product_multiline_description_sale()
            else:
                line.name = ''

    @api.depends('product_id', 'subscription_id.pricelist_id', 'quantity')
    def _compute_price_unit(self):
        for line in self:
            if not line.product_id:
                line.price_unit = 0.0
                continue
            pricelist = line.subscription_id.pricelist_id
            if pricelist:
                price = pricelist._get_product_price(
                    line.product_id,
                    line.quantity or 1.0,
                    currency=pricelist.currency_id,
                )
                line.price_unit = price
            else:
                line.price_unit = line.product_id.lst_price

    @api.depends('product_id', 'company_id')
    def _compute_tax_ids(self):
        for line in self:
            if line.product_id:
                line.tax_ids = line.product_id.taxes_id.filtered(
                    lambda t: t.company_id == line.company_id
                )
            else:
                line.tax_ids = False

    @api.depends('quantity', 'price_unit', 'discount', 'tax_ids')
    def _compute_price_subtotal(self):
        for line in self:
            price = line.price_unit * (1 - line.discount / 100.0)
            taxes = line.tax_ids.compute_all(
                price,
                currency=line.currency_id,
                quantity=line.quantity,
                product=line.product_id,
                partner=line.subscription_id.partner_id,
            )
            line.price_subtotal = taxes['total_excluded']

    def _prepare_invoice_line_values(self):
        self.ensure_one()
        return {
            'product_id': self.product_id.id,
            'name': self.name,
            'quantity': self.quantity,
            'product_uom_id': self.uom_id.id,
            'price_unit': self.price_unit,
            'discount': self.discount,
            'tax_ids': [(6, 0, self.tax_ids.ids)],
        }
