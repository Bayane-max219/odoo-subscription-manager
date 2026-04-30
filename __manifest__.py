{
    'name': 'Subscription Manager',
    'version': '17.0.1.0.0',
    'category': 'Sales/Subscriptions',
    'summary': 'Manage recurring subscriptions with automated billing, renewals and customer portal',
    'description': """
Subscription Manager
====================
A comprehensive recurring subscription management module for Odoo 17.

Key Features:
- Subscription templates with configurable billing cycles (monthly, quarterly, annual)
- Automated renewal via cron with configurable lead time
- Automatic invoice generation linked to subscriptions
- Customer portal with subscription overview
- Kanban view with drag & drop stage management
- QWeb PDF subscription contracts
- Email templates for renewal reminders and confirmations
- Multi-pricelist and multi-currency support
- Subscription analytics dashboard
    """,
    'author': 'Bayane Miguel Singcol',
    'website': 'https://github.com/Bayane-max219/odoo-subscription-manager',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'sale_management',
        'account',
        'portal',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/subscription_stage_data.xml',
        'data/subscription_cron.xml',
        'data/mail_template_data.xml',
        'views/subscription_stage_views.xml',
        'views/subscription_template_views.xml',
        'views/subscription_views.xml',
        'views/res_partner_views.xml',
        'views/subscription_portal_templates.xml',
        'views/menu.xml',
        'wizards/subscription_renew_wizard_views.xml',
        'wizards/subscription_close_wizard_views.xml',
        'reports/subscription_report.xml',
        'reports/subscription_contract_template.xml',
    ],
    'demo': [
        'data/demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'odoo_subscription_manager/static/src/scss/subscription.scss',
        ],
        'web.assets_frontend': [
            'odoo_subscription_manager/static/src/scss/portal.scss',
        ],
    },
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
