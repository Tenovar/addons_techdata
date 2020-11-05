# -*- encoding: utf-8 -*-
import urllib.request
import urllib3
from xml.dom.minidom import Node
from xml.dom.minidom import parse, parseString
import xml.dom.minidom
import socket
import http.client
import time
from odoo import netsvc
from odoo import api, fields, models,tools, _
from odoo.tools import config
from odoo.tools.translate import _
from datetime import datetime, timedelta 
import urllib.request, urllib.error
import xml.etree.ElementTree as ET
from urllib.parse import urlencode
import requests
from requests.structures import CaseInsensitiveDict
import xmltodict
from odoo import http
from odoo.http import request
from odoo.exceptions import UserError, ValidationError

 
    
class ProductCategory(models.Model):
    _name = "product.category"
    _description = "Product Category"
    _inherit = 'product.category'
    code_categ_techdata = fields.Char('Techdata code category',size=255)

class ProductPublicCategory(models.Model):
    _name = "product.public.category"
    _inherit = 'product.public.category'
    _description = "Website Product Category"
    code_categ_techdata = fields.Char('Techdata code category',size=255)
    

class ProductTemplate(models.Model):
    _name = "product.template"
    _description = "Product Template"
    _inherit = 'product.template'
    techdata = fields.Boolean('Techdata Product',readonly=True, default=False)
    last_synchro_techdata = fields.Date("Synchro Date",help="Synchro date",readonly=True)
    ean = fields.Char(string='EAN',help="EAN code")
    manufacturer = fields.Char(string='Manufacturer',help="Manufacturer")
    

    @api.model
    def process_demo_scheduler_queue(self):         
        cr = request.env.cr
        product_template = self.env['product.template'].search([('techdata','=',True)])
        for product in product_template : 
            techdata_config = self.env['techdata.config'].search([('state','=','done')], limit=1)
            print("techdata_config",techdata_config,techdata_config.xml_auth,techdata_config.buyerID)#,product[1],product[19])
            if techdata_config :
                data = prod_qty = line = {}
                url = "https://intcom.xml.quality.techdata.de:7776/Onlchk"
                buyer = techdata_config.buyerID#670979
                auth_code = techdata_config.xml_auth#"e04e5d0c-11c4-4f39-b5ea-b35b38a4f4f5" #techdata_config.xml_auth 
                sku = product.default_code #product[19]
                requete = "<?xml version=\"1.0\" encoding=\"UTF-8\" ?>" 
                requete += "<OnlineCheck>"
                requete += "<Header>"
                requete += "<BuyerAccountId>"+buyer+"</BuyerAccountId>"
                requete += "<AuthCode>"+auth_code+"</AuthCode>"
                requete += "<Type>Full</Type>" 
                requete += "</Header>"
                requete += "<Item line=\"1\">"
                requete += "<ManufacturerItemIdentifier/>"
                requete += "<ResellerItemIdentifier/>"
                requete += "<DistributorItemIdentifier>"+sku+"</DistributorItemIdentifier> "
                requete += "<Quantity>1</Quantity>" 
                requete += "</Item>"               
                requete += "</OnlineCheck> " 
               
                resp = requests.post(url, headers=None, data=requete)
                resp_data = requests.post(url, data=requete, headers=None).text
                if 'Unknown Customer' not in resp_data :
                    #print('Success!')            
                    responseXml = ET.fromstring(resp_data.encode('utf-8'))
                    SystemId = responseXml.find('Header').find('SystemId')
                    AvailabilityTotal = responseXml.find('Item').find('AvailabilityTotal')
                    if AvailabilityTotal.text :
                        UnitPriceAmount = responseXml.find('Item').find('UnitPriceAmount')
                        ProductDesc = responseXml.find('Item').find('ProductDesc')
                        ean_x = responseXml.find('Item').find('EAN')
                        product_id = self.env['product.product']
                        stock_change_product_qty = self.env['stock.change.product.qty']
                        query = """UPDATE product_template SET  description = %s ,list_price = %s,last_synchro_techdata = %s where id = %s"""
                        inputData = (ProductDesc.text, UnitPriceAmount.text,datetime.today(),product.id)#.id)
                        cr.execute(query,inputData)

                        # **************************************************.
                        stock_location = self.env.ref('stock.stock_location_stock')
                        product1 = self.env['product.product'].search([('product_tmpl_id','=',product.id)], limit=1)                      
                        inventory_wizard = self.env['stock.change.product.qty'].create({
                                'product_id': product1.id,
                                'new_quantity': AvailabilityTotal.text,
                                'location_id': stock_location.id,
                            })
                       
                        self.env['stock.inventory'].create({
                                'name': _('INV: %s') % tools.ustr(product1.display_name),
                                'filter': 'product',
                                'location_id': stock_location.id,#stock_location.id,
                                'product_id': product1.id,
                                'state': 'done', 
                            })
                       
                        inventory = self.env['stock.inventory'].search([])[-1].id
                        self.env['stock.inventory.line'].create({
                                'inventory_id': inventory,
                                'product_id': product1.id,
                                'product_qty': AvailabilityTotal.text,
                                'location_id': stock_location.id,
                            })   
                       
                        x_value = float(product1.standard_price) *float(AvailabilityTotal.text)
                        self.env['stock.move'].create({
                                    'name': _('INV:INV:') + product1.display_name,
                                    'product_id': product1.id,
                                    'product_uom_qty': AvailabilityTotal.text or 0,
                                    'product_uom': product1.uom_id.id,#vals['product_uom_id'],
                                    'location_id': product1.property_stock_inventory.id,#'location_id' in product1.property_stock_inventory.id or stock_location.id,#stock_location.id,
                                    'location_dest_id': product1.property_stock_inventory.id,#stock_location.id,#'location_dest_id' in stock_location.id or roduct1.property_stock_inventory.id,#product1.property_stock_inventory.id,
                                    'state': 'done',  
                                    'price_unit' : product1.standard_price,
                                    'inventory_id' :inventory,
                                    'value' : x_value,
                                    #'product_qty': AvailabilityTotal.text,
                            })
                       
                        move = self.env['stock.move'].search([])[-1].id                       
                        self.env['stock.move.line'].create({
                            'move_id': move,
                            'product_id': product1.id,
                            'product_uom_id': product1.uom_id.id,
                            'location_id':product1.property_stock_inventory.id,
                            'location_dest_id': stock_location.id,
                            'state': 'done',
                            'qty_done' :AvailabilityTotal.text, 
                            })
                
                

