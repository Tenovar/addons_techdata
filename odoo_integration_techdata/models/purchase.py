# -*- encoding: utf-8 -*-

import urllib.request
import urllib3
from xml.dom.minidom import Node
from xml.dom.minidom import parse, parseString
import xml.dom.minidom
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

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def product_name_get(self,product_id):
        result = {}
        product_templ = self.env['product.product'].search([('default_code','=',product_id)]).product_tmpl_id
        product_template =self.env['product.template'].search([('id','=',product_templ.id)])
        element = "[%s]" % product_template.default_code
        element = element+product_template.name
        uom = product_template.uom_id
        result.update({'name':element,'uom':uom})
        return result

    def check_product(self,code_product,qty_product): 
        techdata_config = self.env['techdata.config'].search([('state','=','done')], limit=1)
        data={}
        if techdata_config :
                data = prod_qty = line = {}
                url = "https://intcom.xml.quality.techdata.de:7776/Onlchk"
                buyer = techdata_config.buyerID#670979
                auth_code = techdata_config.xml_auth#"e04e5d0c-11c4-4f39-b5ea-b35b38a4f4f5" #techdata_config.xml_auth 
                sku = str(code_product)# '2663149'#product.default_code #product[19]
                x=qty_product
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
                requete += "<DistributorItemIdentifier>{}</DistributorItemIdentifier>".format(sku) 
                requete += "<Quantity>{}</Quantity>".format(int(x)) 
                requete += "</Item>"               
                requete += "</OnlineCheck> " 
               
                resp_data = requests.post(url, data=requete, headers=None).text
                if 'System.FormatException' in resp_data or 'System.OverflowException: Value was either too large or too small for an Int32' in resp_data :
                    raise UserError(_(" error connector EDI ") )
                    return false
                if 'Unknown Customer' not in resp_data :
                    responseXml = ET.fromstring(resp_data.encode('utf-8'))
                    SystemId = responseXml.find('Header').find('SystemId')
                    AvailabilityTotal = responseXml.find('Item').find('AvailabilityTotal')
                    EstimatedDeliveryDate = responseXml.find('Item').find('EstimatedDeliveryDate')
                    UnitPriceAmount = responseXml.find('Item').find('UnitPriceAmount')
                    ProductDesc = responseXml.find('Item').find('ProductDesc')
                    CurrencyCode = responseXml.find('Item').find('CurrencyCode')
                    ean_x = responseXml.find('Item').find('EAN')
                    data.update({
                            'product_id' : sku,                            
                            'AvailabilityTotal' : AvailabilityTotal.text,
                            'ean' : ean_x.text,                                          
                    })                
                return data
                


    def requesteOrder(self,prod,origin,Currency):
            techdata_config = self.env['techdata.config'].search([('state','=','done')], limit=1)
            url = "https://intcom.xml.quality.techdata.de:7776/XMLGate/inbound"
            buyer = techdata_config.buyerID#670979
            auth_code = techdata_config.xml_auth#"e04e5d0c-11c4-4f39-b5ea-b35b38a4f4f5" #techdata_config.xml_auth 
            supplier_id = techdata_config.supplier_id.id
            time = datetime.today().strftime("%Y%m%d%H%M%S")
            time1 = datetime.today().strftime("%Y%m%d")
            date_planned = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
            data_list = []
            msg_id = str(time)+origin+str(time)
            data_list = prod
            compteur =1
            item_prod = ""
            if compteur <= len(prod):
                for line in data_list:
                    item_prod += "<Line ID=\""+str(compteur)+"\">"#.format(str(compteur))
                    item_prod += "<ItemID>{}</ItemID>".format(line['product_id'])
                    item_prod += "<Qty>{}</Qty>".format(int(line['quantity_product']))
                    item_prod += " </Line>"
                    compteur +=1          
            requete = "<?xml version=\"1.0\" encoding=\"UTF-8\" ?>"                 
            requete += "<!DOCTYPE OrderEnv SYSTEM \" http://integratex.quality.techdata.de:8080/ix/dtd/ixOrder4.dtd \">"
            requete += "<OrderEnv AuthCode=\""+auth_code+"\" MsgID=\""+str(msg_id) +"\">"
            requete += "<Order Currency=\""+str(Currency)+"\">"#.format(str(line['cur']))
            requete += "<Head>"
            requete += "<Title>{}</Title>".format(origin)
            requete += "<OrderDate>{}</OrderDate>".format(time1)
            requete += "<DeliverTo>"
            requete += "<Consignee ID=\""+buyer+"\"/>"#.format(str(buyer))
            requete += "</DeliverTo>"
            requete += "<Delivery Type=\"XY\" Full=\"n\" />"
            requete += "</Head>"
            requete += "<Body>"
            requete += "{}".format(item_prod)
            requete += "</Body>"
            requete += " </Order>"
            requete += "</OrderEnv> "
            
            resp_data = requests.post(url, data=requete, headers=None).text
            if 'Unknown Customer' in resp_data or 'Unhandled exception' in resp_data:   
                #raise osv.except_osv(_('ERROR: '),_('Xml request inactive!') )
                print("XGResponse")
            else :
                responseXml = ET.fromstring(resp_data.encode('utf-8'))
                if 'Success' in resp_data :                                      
                    message = _("Techdata : Success title=XML Message received. OrderNumber = %s, MessageID = %s ") % (origin,msg_id)                    
                    self.message_post(body=message)                                                             
                elif 'Failure' in resp_data:
                    raise UserError(_(" error XML request  "))      
    @api.multi
    def button_confirm(self): 
        data_list =  []
        techdata_config = self.env['techdata.config'].search([('state','=','done')], limit=1) 
        supplier_id = techdata_config.supplier_id
        if supplier_id.id == self.partner_id.id:
            purchase_order_line =  self.env['purchase.order.line'].search([('order_id','=',self.id)])
            for item in purchase_order_line :  
                if item.product_id.techdata == True:                
                  list_product = self.check_product(item.product_id.default_code,item.product_uom_qty) 
                  list_product['quantity_product'] =   item.product_uom_qty           
                  list_product['cur'] =   item.currency_id.name 
                  data_list.append(list_product)
            if data_list:
              self.requesteOrder(data_list,self.name,self.env.ref('base.main_company').currency_id.name) 
              date_schedule = self.date_planned + timedelta(days=10)
              self.env['stock.picking'].search([('origin','=',self.origin)]).write({'scheduled_date':date_schedule})
        res = super(PurchaseOrder, self).button_confirm()
        return res             
