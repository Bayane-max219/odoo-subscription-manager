from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.translate import _


class Subscription(models.Model):
    _name = 'subscription.subscription'
    _description = 'Subscription'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'date_start desc, id desc'
    _rec_name = 'display_name'

    # -------------------------------------------------------------------------
    # Identification
    # -------------------------------------------------------------------------
    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )
    display_name = fields.Char(compute='_compute_display_name', store=True)
    template_id = fields.Many2one(
        'subscription.template',
        string='Template',
        required=True,
        ondelete='restrict',
        tracking=True,
    )
    stage_id = fields.Many2one(
        'subscription.stage',
        string='Stage',
        group_expand='_read_group_stage_ids',
        ondelete='restrict',
        tracking=True,
        index=True,
        copy=False,
    )
    kanban_state = fields.Selection([
        ('normal', 'In Progress'),
        ('done', 'Ready for Renewal'),
        ('blocked', 'Blocked'),
    ], default='normal', tracking=True)

    # -------------------------------------------------------------------------
    # Relations
    # -------------------------------------------------------------------------
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        tracking=True,
        index=True,
    )
    user_id = fields.Many2one(
        'res.users',
        string='Salesperson',
        default=lambda self: self.env.user,
        tracking=True,
    )
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
    )
    pricelist_id = fields.Many2one(
        'product.pricelist',
        string='Pricelist',
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='pricelist_id.currency_id',
        store=True,
    )
    tag_ids = fields.Many2many('subscription.tag', string='Tags')
    line_ids = fields.One2many(
        'subscription.line',
        'subscription_id',
        string='Subscription Lines',
        copy=True,
    )
    invoice_ids = fields.One2many(
        'account.move',
        'subscription_id',
        string='Invoices',
        copy=False,
    )

    # -------------------------------------------------------------------------
    # Dates
    # -------------------------------------------------------------------------
    date_start = fields.Date(
        string='Start Date',
        required=True,
        default=fields.Date.today,
        tracking=True,
    )
    date_end = fields.Date(
        string='End Date',
        tracking=True,
        help='Leave empty for indefinite subscription.',
    )
    next_invoice_date = fields.Date(
        string='Next Invoice Date',
        copy=False,
        tracking=True,
    )
    next_renewal_date = fields.Date(
        string='Next Renewal Date',
        compute='_compute_next_renewal_date',
        store=True,
    )
    close_date = fields.Date(string='Close Date', copy=False)

    # -------------------------------------------------------------------------
    # Financials
    # -------------------------------------------------------------------------
    recurring_total = fields.Monetary(
        string='Recurring Total',
        compute='_compute_recurring_total',
        store=True,
        currency_field='currency_id',
    )
    invoice_count = fields.Integer(
        compute='_compute_invoice_count',
        string='Invoices',
    )
    paid_invoice_count = fields.Integer(
        compute='_compute_invoice_count',
        string='Paid Invoices',
    )
    total_invoiced = fields.Monetary(
        compute='_compute_total_invoiced',
        string='Total Invoiced',
        currency_field='currency_id',
    )

    # -------------------------------------------------------------------------
    # Settings inherited from template
    # -------------------------------------------------------------------------
    billing_cycle = fields.Selection(
        related='template_id.billing_cycle',
        store=True,
    )
    auto_renew = fields.Boolean(
        related='template_id.auto_renew',
        store=True,
    )
    renewal_lead_days = fields.Integer(
        related='template_id.renewal_lead_days',
        store=True,
    )
    invoice_policy = fields.Selection(
        related='template_id.invoice_policy',
        store=True,
    )

    # -------------------------------------------------------------------------
    # Notes
    # -------------------------------------------------------------------------
    note = fields.Html(string='Internal Notes')
    close_reason = fields.Text(string='Close Reason', copy=False)

    # =========================================================================
    # Compute methods
    # =========================================================================

    @api.depends('partner_id', 'name')
    def _compute_display_name(self):
        for sub in self:
            sub.display_name = f'{sub.name} - {sub.partner_id.name}' if sub.partner_id else sub.name

    @api.depends('line_ids.price_subtotal')
    def _compute_recurring_total(self):
        for sub in self:
            sub.recurring_total = sum(sub.line_ids.mapped('price_subtotal'))

    @api.depends('date_end', 'template_id.renewal_lead_days')
    def _compute_next_renewal_date(self):
        for sub in self:
            if sub.date_end and sub.renewal_lead_days:
                sub.next_renewal_date = sub.date_end - timedelta(days=sub.renewal_lead_days)
            else:
                sub.next_renewal_date = False

    def _compute_invoice_count(self):
        for sub in self:
            invoices = sub.invoice_ids.filtered(
                lambda m: m.move_type == 'out_invoice'
            )
            sub.invoice_count = len(invoices)
            sub.paid_invoice_count = len(
                invoices.filtered(lambda m: m.payment_state == 'paid')
            )

    def _compute_total_invoiced(self):
        for sub in self:
            sub.total_invoiced = sum(
                sub.invoice_ids.filtered(
                    lambda m: m.move_type == 'out_invoice' and m.state == 'posted'
                ).mapped('amount_total')
            )

    def _compute_access_url(self):
        for sub in self:
            sub.access_url = f'/my/subscriptions/{sub.id}'

    # =========================================================================
    # ORM overrides
    # =========================================================================

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'subscription.subscription'
                ) or _('New')
            if not vals.get('stage_id'):
                vals['stage_id'] = self._get_default_stage_id()
        return super().create(vals_list)

    def _get_default_stage_id(self):
        stage = self.env['subscription.stage'].search(
            [('category', '=', 'draft')], limit=1, order='sequence asc'
        )
        return stage.id if stage else False

    # =========================================================================
    # Actions
    # =========================================================================

    def action_start(self):
        active_stage = self.env['subscription.stage'].search(
            [('category', '=', 'in_progress')], limit=1, order='sequence asc'
        )
        if not active_stage:
            raise UserError(_('No active stage found. Please configure subscription stages.'))
        for sub in self:
            sub.stage_id = active_stage
            if not sub.next_invoice_date:
                sub.next_invoice_date = sub.date_start
            sub.message_post(
                body=_('Subscription started.'),
                message_type='notification',
            )

    def action_close(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'subscription.close.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_subscription_ids': self.ids},
        }

    def action_renew(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'subscription.renew.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_subscription_ids': self.ids,
                'default_new_date_end': self._compute_new_end_date(),
            },
        }

    def action_view_invoices(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoices'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('subscription_id', '=', self.id), ('move_type', '=', 'out_invoice')],
        }

    # =========================================================================
    # Invoicing
    # =========================================================================

    def _compute_new_end_date(self):
        self.ensure_one()
        if not self.date_end:
            return False
        cycle_days = self.template_id.get_cycle_days()
        if self.billing_cycle == 'monthly':
            return self.date_end + relativedelta(months=1)
        elif self.billing_cycle == 'quarterly':
            return self.date_end + relativedelta(months=3)
        elif self.billing_cycle == 'biannual':
            return self.date_end + relativedelta(months=6)
        elif self.billing_cycle == 'annual':
            return self.date_end + relativedelta(years=1)
        else:
            return self.date_end + timedelta(days=cycle_days)

    def _prepare_invoice_values(self):
        self.ensure_one()
        journal = self.env['account.journal'].search(
            [('type', '=', 'sale'), ('company_id', '=', self.company_id.id)],
            limit=1,
        )
        invoice_lines = []
        for line in self.line_ids:
            invoice_lines.append((0, 0, line._prepare_invoice_line_values()))
        return {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'journal_id': journal.id,
            'invoice_date': date.today(),
            'invoice_line_ids': invoice_lines,
            'subscription_id': self.id,
            'narration': f'Subscription {self.name}',
        }

    def _create_invoice(self):
        self.ensure_one()
        vals = self._prepare_invoice_values()
        invoice = self.env['account.move'].create(vals)
        cycle_days = self.template_id.get_cycle_days()
        if self.billing_cycle == 'monthly':
            self.next_invoice_date = (self.next_invoice_date or date.today()) + relativedelta(months=1)
        elif self.billing_cycle == 'quarterly':
            self.next_invoice_date = (self.next_invoice_date or date.today()) + relativedelta(months=3)
        elif self.billing_cycle == 'biannual':
            self.next_invoice_date = (self.next_invoice_date or date.today()) + relativedelta(months=6)
        elif self.billing_cycle == 'annual':
            self.next_invoice_date = (self.next_invoice_date or date.today()) + relativedelta(years=1)
        else:
            self.next_invoice_date = (self.next_invoice_date or date.today()) + timedelta(days=cycle_days)
        return invoice

    # =========================================================================
    # Cron methods
    # =========================================================================

    @api.model
    def _cron_generate_invoices(self):
        """Called daily by cron. Generates invoices for subscriptions due today."""
        today = date.today()
        subscriptions = self.search([
            ('stage_id.category', '=', 'in_progress'),
            ('next_invoice_date', '<=', today),
        ])
        invoices = self.env['account.move']
        for sub in subscriptions:
            try:
                invoice = sub._create_invoice()
                invoices |= invoice
            except Exception as e:
                sub.message_post(
                    body=_('Failed to generate invoice: %s') % str(e),
                    message_type='notification',
                    subtype_xmlid='mail.mt_note',
                )
        if invoices:
            invoices.action_post()
        return True

    @api.model
    def _cron_send_renewal_reminders(self):
        """Called daily. Sends renewal reminder emails for subscriptions nearing expiry."""
        today = date.today()
        subscriptions = self.search([
            ('stage_id.category', '=', 'in_progress'),
            ('auto_renew', '=', False),
            ('date_end', '!=', False),
            ('next_renewal_date', '<=', today),
        ])
        template = self.env.ref(
            'odoo_subscription_manager.mail_template_renewal_reminder',
            raise_if_not_found=False,
        )
        for sub in subscriptions:
            if template:
                template.send_mail(sub.id, force_send=True)

    @api.model
    def _cron_auto_renew(self):
        """Called daily. Auto-renews subscriptions configured with auto_renew."""
        today = date.today()
        subscriptions = self.search([
            ('stage_id.category', '=', 'in_progress'),
            ('auto_renew', '=', True),
            ('date_end', '!=', False),
            ('next_renewal_date', '<=', today),
        ])
        for sub in subscriptions:
            new_date_end = sub._compute_new_end_date()
            sub.write({'date_end': new_date_end})
            sub.message_post(
                body=_('Subscription automatically renewed. New end date: %s') % new_date_end,
                message_type='notification',
            )

    # =========================================================================
    # Kanban grouping
    # =========================================================================

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        return self.env['subscription.stage'].search([], order=order)
