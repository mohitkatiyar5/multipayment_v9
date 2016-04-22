{
    'name': 'Petrofig-Charting',
    'version': '1.0',
    'category': 'Account Payment',
    'description': """
      rosso voyage ship module
""",
    'author': 'openerp4you',
    'depends': ['base','base_setup','sale','account', 'product', 'analytic', 'board', 'report','purchase'],
    'data': [
        'wizard/wiz_invoice_lines_view.xml',
        'custom_account_payment_view.xml',
        'sequence/payment_sequence.xml',
        'security/ir.model.access.csv', 
        'report/acc_payment_report_menu.xml',
        'report/acc_payment_report_view.xml',
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}
