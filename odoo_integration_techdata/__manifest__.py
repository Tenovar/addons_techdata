# -*- encoding: utf-8 -*-

{
    "name": "Techdata XML integration",
    "version": "12.1.1",
    "depends": ["base","sale_management","website_product_publish","product_image_url","product","stock","purchase"],
    "author": "TenovarLTD",
    "category": "Generic Modules/Others",
    "description": """
    This module provides an XML integration between OpenERP and Techdata . 
    It allows to maintain the Techdata product catalog and price list up to date automatically. 
    It also provides a real-time integration for quotation, sales, purchases and deliveries. 
    Actions in OpenERP generate requests toward Techdata to get informations, or to place an order directly, 
    without using any external tool or website.     
    """,
    "data": [
        'security/connector_security.xml',
        'security/ir.model.access.csv',
        #'views/connector_menu.xml',
        'data/service_cron_reverse.xml',
        'views/techdata_config_view.xml',
        'views/product_view.xml',
        'views/sale_view.xml',
        'views/purchase_view.xml',

    ],     
    'installable': True,
    'application': True,
    'auto_install': False,   
}


