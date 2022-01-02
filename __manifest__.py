# -*- coding: utf-8 -*-
{
    'name': "Enz E-WAY/E-INVOICE",
    'author':
        'YARMIZ',
    'summary': """
This module will help to assign the targets to sales persons
""",

    'description': """
        Long description of module's purpose
    """,
    'website': "",
    'category': 'base',
    'version': '12.0',
    'depends': ['base','account',"stock","sale","contacts","ezp_estimate"],
    "images": ['static/description/icon.png'],
    'data': [
        'security/ir.model.access.csv',
        'data/seq.xml',
        'views/eway_config.xml',
        'views/transportation.xml',
        'views/sale.xml',
        'views/consolidate.xml',
        'views/account.xml',
        'views/irn_cancel.xml',
        'views/get_tax_payers.xml',
        'views/synchronize_gstin.xml',
        'views/get_eway_details_by_irn.xml',
        'views/get_irn_details_by_docs.xml',
        'views/get_eway_transporter_by_gst.xml',
        'views/get_eway_transporter.xml',
        'views/get_eway_other.xml',
        'views/get_consolidated.xml',
        'report/isr_report.xml',
        'report/eay.xml',
        'report/eay_inv.xml',
        'report/einv_invoice_report.xml',

    ],
    'demo': [
    ],
    'installable': True,
    'application': True,
}
