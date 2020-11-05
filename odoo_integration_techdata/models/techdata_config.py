# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
_logger = logging.getLogger(__name__)
from datetime import datetime, timedelta
from functools import partial
from itertools import groupby
import base64
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import formatLang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare
import ftplib
from odoo.addons import decimal_precision as dp
from werkzeug.urls import url_encode
import urllib.request, urllib.error
import xml.etree.ElementTree as ET
from urllib.parse import urlencode
import requests
from requests.structures import CaseInsensitiveDict
from odoo.http import request
import odoo.exceptions
import odoo.osv.osv
from glob import glob as gg
from zipfile import ZipFile 
  
import os.path
import os
import csv, math
import codecs
class TechdataConfig(models.Model):
    _name = "techdata.config"
    _description = "Configuration Management Produces Techdata"    
    #_columns={
    name = fields.Char("Name",size=255,help="Name associated with the configuration", readonly=False,states={'done': [('readonly', True)]})
    sku_Product = fields.Char('SKU Product Techdata',size=255,help="we need to enter valid SKU Product to check connexion",readonly=False,states={'done': [('readonly', True)]})
    xml_address = fields.Char('Server Xml address',size=255,help="server Xml address",readonly=False,states={'done': [('readonly', True)]})
    xml_host = fields.Char('Host',size=255,help="Host for Xml request ",readonly=False,states={'done': [('readonly', True)]})
    xml_auth = fields.Char('CodeAuth',size=255,help="Authorisation code for Xml request ",readonly=False,states={'done': [('readonly', True)]})
    buyerID = fields.Char('Buyer ID',size=255,help="Buyer ID ",readonly=False,states={'done': [('readonly', True)]})
    techdata_login = fields.Char('Login',size=255,help="Login Techdata",readonly=False,states={'done': [('readonly', True)]})
    techdata_passwd = fields.Char('Password',size=255,help="Password Techdata",readonly=False,states={'done': [('readonly', True)]})
    country_id = fields.Many2one('res.country', 'Country',help=" Country of techdata supplier",readonly=False,states={'done': [('readonly', True)]})
    state = fields.Selection([
        ('draft', 'Not Confirmed'),
        ('done', 'Confirmed'),
    ], string='Status', index=True, readonly=True, copy=False, default='draft')

    location_id = fields.Many2one('stock.location', 'Location', required=True, domain="[('usage', '=', 'internal')]",help=" Location of new product")
    #country_id = fields.Many2one('res.country', 'Country', required=True,help=" Country of Ingram supplier")
    categorie_id =fields.Many2one('product.category','Category', required=True, change_default=True ,help="Select category for the current product")
    supplier_id = fields.Many2one('res.partner', 'Supplier', required=True,domain = [('supplier','=',True)], ondelete='cascade', help="Supplier of this product")
    
    chemin = fields.Char("Path",siz=255,help="Path where the files is stored")
    server_address =  fields.Char('Server address',size=255,help="server ip address")
    server_login =  fields.Char('Login',size=255,help="Login database")
    server_passwd = fields.Char('Password',size=255,help="Password database")
    date_synchro =  fields.Datetime('Date of last manually synchronization',readonly=True)
    date_import = fields.Datetime('Date of last manually importation',readonly=True)
    file_cat = fields.Char('Products Categories file name',size=255,help="Name of the file for the products categories")
    file_prod = fields.Char('Products File name',size=255,help="Name of the file for the products. Must be based on this header: 'Techdata Part Number,Vendor Part Number,EANUPC Code,Plant,Vendor Number,Vendor Name,Weight,Category ID,Customer Price,Retail Price,Availability Flag,BOM Flag,Warranty Flag,Material Long Description,Material Creation Reason code,Material Language Code,Music Copyright Fees,Recycling Fees,Document Copyright Fees,Battery Fees,Availability (Local Stock),Availability (Central Stock),Creation Reason Type,Creation Reason Value,Local Stock Backlog Quantity,Local Stock Backlog ETA,Central Stock Backlog Quantity,Central Stock Backlog ETA'")

    @api.multi
    def button_confirm_login(self):        
            try:
                url = self.xml_host#"https://intcom.xml.quality.techdata.de:7776/Onlchk"
                buyer = self.buyerID#670979
                auth_code = self.xml_auth#"e04e5d0c-11c4-4f39-b5ea-b35b38a4f4f5" #techdata_config.xml_auth 
                sku = self.sku_Product#.default_code
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
                # resp = requests.post(url, headers=None, data=requete)
                resp_data = requests.post(url, data=requete, headers=None).text
                if 'Unknown Customer' not in resp_data :
                    self.write({'state': 'done'})                     
                else:
                    raise UserError(_(" please check Authorisation code , code buyer,... ") ) 

            except Exception as err:
                _logger.info("Failed to connect to Techdata .")
                raise UserError(_("Connection failed: %s") % tools.ustr(err))   
            return True          
    
    @api.multi
    def set_draft(self):
        self.write({'state': 'draft'})
        return True    
   
    @api.model
    def create(self,vals):
        ids=self.search([])        
        if len(ids)>0:
            raise UserError("You can have only one configuration.")
        return super(TechdataConfig, self).create(vals)

    def check_ftp(self):
        if self._context is None:
            self._context = {}
        #ingrams = self.browse(cr, uid, ids)
        config = self.read(['server_address','server_login','server_passwd','chemin'])
        ip = config[0]['server_address']
        login = config[0]['server_login']
        passwd = config[0]['server_passwd']
        chm=str(config[0]['chemin'])
        try:
            ftp=ftplib.FTP()
        except:
            raise odoo.osv.osv.except_osv(_('Error!'), _("FTP was not started!"))
            return False
        ip=ip.split('/')
        txt=""
        for i in range(len(ip)):
           if i>0:
                txt+="/"+ip[i]
        try:
            ftp.connect(ip[0])
            if login:
                ftp.login(login,passwd)
            else:
                ftp.login()
        except:
            raise odoo.osv.osv.except_osv(_('Error!'), _("Username/password FTP connection was not successfully!"))
            return False
        ftp.close()
        raise odoo.osv.osv.except_osv(_('Ok!'), _("FTP connection was successfully!")) 
        return True

    def button_import_data(self):
        view = self.browse(self._ids)
        name_config = view[0].name 
        time=datetime.now() 

        # val=self.browse(self._ids)[0].synchro_active
        # if not val :
        id_config = self.search([('name','=',name_config),])
        _logger.info('Download started')        
        result=self.import_data(id_config)
        if result==True:
            _logger.info('Download ended')
            try :                
                self.search([('id','=',id_config)]).write({'date_import' : time.strftime("%Y-%m-%d %H:%M:%S")})
            except:
                try :                    
                    self.search([('id','=',id_config)]).write({'date_import' : time.strftime("%Y-%m-%d %H:%M:%S")})
                except:pass
        else:
            _logger.info('Download error')
            return False
        
        return True
    
    def import_data(self,id_config):
        config = self.env['techdata.config'].search([('id','=',id_config.id)]).read(['server_address','server_login','server_passwd','chemin'])        
        ip = config[0]['server_address']        
        login = config[0]['server_login']
        passwd = config[0]['server_passwd']
        chm=str(config[0]['chemin'])       

        # i = config[0]['file_cat']
        
        
        try:
            ftp=ftplib.FTP()
        except:
            _logger.error('connection error')
            self.sendTextMail(id_config,"Connecion error","An error occured during the connection to the server.\n\nDetails: \n\t %s" %(sys.exc_info()[0]))
            return False
        ip=ip.split('/')
        txt=""
        for i in range(len(ip)):
            if i>0:
                txt+="/"+ip[i]
        try:
            ftp.connect(ip[0])
            if login:
                ftp.login(login,passwd)
            else:
                ftp.login()
            ftp.retrlines('LIST')
            
            ftp.cwd(txt)
            
            ftp.retrlines('LIST')
            
            self.download(id_config,'.',chm,ftp)
            ftp.close()
                
            return True
        except:
           _logger.error('Download error')
           #self.sendTextMail(cr,uid,id_config,"Import error","An error occured during the importation.\n\nDetails: \n\t %s" %(sys.exc_info()[0]))
           return False
    #

    
   
    def synchro_data(self):
        view = self.browse(self._ids)
        
        name_config = view[0].name        
        id_config = self.search([('name','=',name_config),])
        config = self.read([id_config,'server_address','server_login','server_passwd','chemin'])
        #val=self.browse(self._ids)[0].synchro_active
        product_categ=self.env['product.category']
        time=datetime.now()

        # *** create categories 
        _logger.info('Products categories synchronization started')
        result=self.synchro_categ(id_config)
        if result==True:
            _logger.info('products categories synchronization ended')
        else:
            _logger.info('products categories synchronization error')
            return False     
        # # *** create Products 
        _logger.info('products synchronization started')
        result3=self.synchronisation(id_config)        
        _logger.info(result3)
        if result3==True:
            _logger.info('products synchronization ended')
        else:
            _logger.info('products synchronization error')
            return False
        #self.clean_categ(id_config)
        try :
            self.search([('id','=',id_config)]).write({'date_synchro' : time.strftime("%Y-%m-%d %H:%M:%S")})
        except:
            try :
                self.search([('id','=',id_config)]).write({'date_synchro' : time.strftime("%Y-%m-%d %H:%M:%S")})
            except:pass
        return True

        
    def synchronisation(self,id_config):  
        #config = self.read([id_config,'server_address','server_login','server_passwd','location_id','categorie_id','chemin','file_prod'])
        config = self.env['techdata.config'].search([('id','=',id_config.id)]).read(['server_address','supplier_id','server_login','server_passwd','location_id','categorie_id','chemin','file_prod'])
        location = config[0]['location_id']
        categ = config[0]['categorie_id']
        supplier= config[0]['supplier_id']
        chm=str(config[0]['chemin'])
        file_prod=config[0]['file_prod']
        listefich = os.listdir(chm+'/')
        date=datetime.now()
        product_product=self.env['product.product']
        product_categ=self.env['product.category']
        product_tmpl=self.env['product.template']
        product_public_category = self.env['product.public.category']
        stock_location_route = self.env['stock.location.route'].search([('name','=','Make To Order')])
        time=datetime.now()  
        cr = request.env.cr 
        try:
            compteur=0            
            for i in listefich:                
                if str(i) == 'price.zip':                     
                    # specifying the zip file name 
                    file_name1 = chm+'\\'+str(i)                         
                    # opening the zip file in READ mode 
                    
                    with ZipFile(file_name1, 'r') as zip: 
                        # printing all the contents of the zip file                                                        
                        zip.printdir()  
                        listOfFileNames = zip.namelist()
                        arr = os.listdir(chm)                        
                        for file_itel in arr :
                                                                      
                            if file_itel == file_prod :
                                f_name = chm+'\\'+str(file_itel)
                                os.remove(f_name)
                                print("File Removed!")
                        #extracting all the files                         
                        print('Extracting all the files now...')                       
                        zip.extractall(path=chm, members=None, pwd=None)
                        print('Done!')                
            listefich = os.listdir(chm+'/')
            
            for i in listefich:
                if str(i)==str(file_prod):
                    fichier = open(chm+'/'+i,'rb')                    
                    #fichiercsv = csv.reader(fichier, delimiter=',')
                    fichiercsv = csv.reader(codecs.iterdecode(fichier, 'unicode_escape'),  delimiter="\t")                    
                    for ligne in fichiercsv:
                        if ligne[0] != "ProdNr":                                                      
                            nom=ligne[1]+'-'+ligne[2]#name[0:127]
                            desc=ligne[3]#name                           
                            date_str1 = str(ligne[7])
                            date_str2=str(ligne[9])     
                            a17 = ligne[17]
                            b18 = ligne[18]
                            c13 = ligne[13]                           
                            if  date_str2 and date_str2 : 
                                date_dt1 = datetime.strptime(date_str1, '%d/%m/%Y %H:%M:%S')
                                date_dt2 = datetime.strptime(date_str2, '%d/%m/%Y')
                                delivery = abs(date_dt2-date_dt1).days
                            else:
                                delivery = 0.0 
                            _logger.info(compteur)
                            empl = product_product.search([('default_code','=',ligne[0]),])

                            if empl:                                 

                                resultas =product_product.search([('id','=',empl.id),])
                                idprod = resultas[0]['product_tmpl_id'] 
                                categ_techdata=product_categ.search([('id','=',resultas[0]['product_tmpl_id'].categ_id.id)])
                                if float(ligne[5]) == 0 :
                                    list_price = float(ligne[4]) * 1.25
                                else :
                                    list_price = float(ligne[5])
                                product_tmpl.search([('id','=',idprod.id)]).write({'name':nom,'sale_delay':delivery,'manufacturer':ligne[2],'ean':ligne[15],'list_price':list_price,'standard_price':float(ligne[4]),'weight':float(ligne[20]),'description':desc,
                                                                    'categ_id':categ_techdata[0].id,'last_synchro_techdata':time.strftime("%Y-%m-%d %H:%M:%S")})
                                
                                suppinfo_id=product_tmpl.browse(idprod.id).seller_ids                                
                               
                                for b in suppinfo_id:
                                    if b.name.id == supplier[0]:
                                        exist=b.id
                                        if not b.product_name or not b.product_code:
                                            self.env['product.supplierinfo'].search([('id','=',b.id),]).write({'product_name':nom,'product_code':ligne[0],'price':float(ligne[4])})
                                                                    
                                #product_product.search([('id','=',empl.id)]).write({'manufacturer':ligne[2]})                                
                            else:        
                                    data = []
                                    url_product =("https://live.icecat.biz/api/?UserName=openIcecat-live&Language=en&Brand=%s&ProductCode=%s" % (ligne[2],ligne[1]))#.format(ligne[2],ligne[1])
                                    resp = requests.get(url_product)
                                    data = resp.json()
                                    web_url = ''
                                    image = ''                                    
                                    data_msg = '' 
                                    if data :                                        
                                        if 'statusCode' in data or  'Error' in data :                                            
                                            data_msg =  ''
                                        elif data['data'] :
                                                data_msg = data['msg']                                                                    
                                        if data_msg :
                                            if  data['data']['Image'] :
                                                if data['data']['Image']['LowPic'] != "0" :
                                                    web_url=data['data']['Image']['LowPic'] 
                                                    image = base64.b64encode(requests.get(web_url).content)                
                                    p1=product_categ.search([('code_categ_techdata','=',ligne[17])],limit=1)                                    
                                    
                                    p2=product_categ.search([('code_categ_techdata','=',ligne[13]),('parent_id','=',p1.id)],limit=1)                                      
                                    
                                    p3=product_categ.search([('code_categ_techdata','=',ligne[18]),('parent_id','=',p2.id)],limit=1)                                    
                                    
                                    parent_path =p3.parent_path#p_path+'/'+str(p1.id)+'/'+str(p2.id)+'/'+str(p3.id)+'/'                                    
                                    categ_techdata = product_categ.search([('parent_path','=',parent_path)]) 
                                    
                                    if not categ_techdata:
                                        categ_techdata=categ
                                    pwc1=product_public_category.search([('code_categ_techdata','=',a17)],limit=1)                                    
                                    pwc2=product_public_category.search([('code_categ_techdata','=',c13),('parent_id','=',pwc1.id)],limit=1)                                      
                                    pwc3=product_public_category.search([('code_categ_techdata','=',b18),('parent_id','=',pwc2.id)],limit=1)                                    
                                    parent_path_website =p3.parent_path#p_path+'/'+str(p1.id)+'/'+str(p2.id)+'/'+str(p3.id)+'/'                                       
                                    categ_website_techdata = product_public_category.search([('parent_id','=',pwc2.id)])   
                                    if float(ligne[5]) == 0 :
                                        list_price = float(ligne[4]) * 1.25
                                    else :
                                        list_price = float(ligne[5])
                                    id=product_tmpl.create({'default_code':ligne[0],'web_url':web_url,'image_medium': image,'name':nom,'manufacturer':ligne[2],'ean':ligne[15],'list_price':list_price,'sale_delay':float(delivery),'standard_price':float(ligne[4]),'weight':float(ligne[20]),'description':desc,
                                        'categ_id':categ_techdata.id,"public_categ_ids":[[ 6, 0, [pwc3.id] ]],'techdata':True,'type':'product','last_synchro_techdata':time.strftime("%Y-%m-%d %H:%M:%S")})
                                    
                                    #product_tmpl.search([('id','=',id.id)]).write({'route_ids':[[ 6, True, [stock_location_route.id] ]]})


                                    seller_ids = product_product.search([('product_tmpl_id','=',id.id)])
                                    
                                    self.env['product.supplierinfo'].create({'name':supplier[0],'min_qty':0,'product_tmpl_id':id.id,'price':float(ligne[4]),'product_id':product_product.id,'product_name':nom,'product_code':ligne[0],})
                                    product_tmpl.search([('id','=',id.id)]).write({'seller_ids':seller_ids})
                                    
                                    # ** Product Iages e-commerce 
                                    #if data_msg  and data['data']['Image']: #not 'statusCode' in data and data['data']['Image'] and not 'Error' in data :
                                    if data_msg :
                                        
                                        if  data['data']['Image'] :
                                        
                                            if data['data']['Image']['HighPic'] :                                                
                                                image_HighPic = data['data']['Image']['HighPic'] 
                                                image_HighPic1 = base64.b64encode(requests.get(image_HighPic).content) 
                                                self.env['product.image'].create({'name':nom,'image':image_HighPic1,'product_tmpl_id':id.id})
                                            if data['data']['Image']['Pic500x500'] :                                                
                                                image_Pic500 = data['data']['Image']['Pic500x500']                                           
                                                image_Pic5001 = base64.b64encode(requests.get(image_Pic500).content) 
                                                self.env['product.image'].create({'name':nom,'image':image_Pic5001,'product_tmpl_id':id.id}) 
                                            
                                            
                                    # *********************

                            
                            if float(ligne[8]) > 0  :
                                   
                                    stock_location = self.env.ref('stock.stock_location_stock')
                                    empl = self.env['product.product'].search([('default_code','=',ligne[0])], limit=1)                                                        
                                    inventory_wizard = self.env['stock.change.product.qty'].create({
                                            'product_id': empl.id,#product1.id,
                                            'new_quantity': float(ligne[8]),# AvailabilityTotal.text,
                                            'location_id': stock_location.id,
                                        })
                            
                                    self.env['stock.inventory'].create({
                                            'name': _('INV: %s') % tools.ustr(empl.display_name),
                                            'filter': 'product',
                                            'location_id': stock_location.id,#stock_location.id,
                                            'product_id': empl.id,#product1.id,
                                            'state': 'done', 
                                        })
                                  
                                    inventory = self.env['stock.inventory'].search([])[-1].id
                                    self.env['stock.inventory.line'].create({
                                            'inventory_id': inventory,
                                            'product_id': empl.id,#product1.id,
                                            'product_qty': float(ligne[8]),# AvailabilityTotal.text,
                                            'location_id': stock_location.id,
                                        })   
                                    
                                    x_value = float(empl.standard_price) *float(ligne[8])
                                    self.env['stock.move'].create({
                                                'name': _('INV:INV:') + empl.display_name,
                                                'product_id': empl.id,#product1.id,
                                                'product_uom_qty': float(ligne[8]) or 0,# AvailabilityTotal.text,AvailabilityTotal.text or 0,
                                                'product_uom': empl.uom_id.id,#vals['product_uom_id'],
                                                'location_id': empl.property_stock_inventory.id,#'location_id' in product1.property_stock_inventory.id or stock_location.id,#stock_location.id,
                                                'location_dest_id': empl.property_stock_inventory.id,#stock_location.id,#'location_dest_id' in stock_location.id or roduct1.property_stock_inventory.id,#product1.property_stock_inventory.id,
                                                'state': 'done',  
                                                'price_unit' : empl.standard_price,
                                                'inventory_id' :inventory,
                                                'value' : x_value,
                                                #'product_qty': AvailabilityTotal.text,
                                        })
                                 
                                    move = self.env['stock.move'].search([])[-1].id                       
                                    self.env['stock.move.line'].create({
                                        'move_id': move,
                                        'product_id': empl.id,#product1.id,
                                        'product_uom_id': empl.uom_id.id,
                                        'location_id':empl.property_stock_inventory.id,
                                        'location_dest_id': stock_location.id,
                                        'state': 'done',
                                        'qty_done' : float(ligne[8]),#AvailabilityTotal.text, 
                                       })
                                   
                        compteur+=1

                    fichier.close()
            return True       
        except:            
            _logger.error("Erreur Synchro_produit")
            #self.sendTextMail(cr,uid,id_config,"Error Synchronization","An error occured during the synchronization.\n \nDetails: \n\t %s" %(sys.exc_info()[0]))
            return False                
        
    def download(self,id_config,pathsrc, pathdst,ftp):
        idss=self.browse(id_config[0])
              
        try:
            lenpathsrc = len(pathsrc)
            l = ftp.nlst(pathsrc) 
            for i in l:
                tailleinit=ftp.size(i) 
                if ((str(i)==str(idss.file_cat))): 
                    ftp.size(i)
                    #ftp.retrbinary('RETR '+i, open(pathdst+os.sep+i, 'wb').write)     

                if ((str(i)==str(idss.file_cat)) or str(i)==str(idss.file_prod)):
                    try:
                        ftp.size(i)
                        ftp.retrbinary('RETR '+i, open(pathdst+os.sep+i, 'wb').write)                  
                    except:
                        try: os.makedirs(pathdst+os.sep+os.path.dirname(i[lenpathsrc:]))
                        except: pass
                        return False
                    if os.path.isfile(pathdst+'/'+i) :                        
                        taille=os.path.getsize(pathdst+'/'+i)
                        if (tailleinit!=taille):
                            os.remove(pathdst+'/'+i)
            return True
        except:
            return False    
   
    def product_qty(self,qty,prod_id,location):
        time=datetime.now()
        date = time.strftime("%Y-%m-%d %H:%M:%S")
        listid = self.env['stock.inventory'].search([('name','=','INV Techdata'+str(time.strftime("%Y-%m-%d")))])
        if (listid):
            id_Inv=listid[0]
        else:            
            id_Inv=self.env['stock.inventory'].create({'state':'draft','name':'INV Techdata'+str(time.strftime("%Y-%m-%d")),'date_done':date,'write_date':date})
        self.env['stock.inventory.line'].create({'compagny_id':1,'inventory_id':int(id_Inv),'product_qty':qty,'location_id':location,'product_id': int(prod_id),'product_uom' : 1})
        return True   
      
   
    def sync_product_cron(self):       
        product_categ=self.env['product.category']
        time=datetime.now()       
        id_config = self.env['techdata.config'].search([],limit=1)
        
        _logger.info('Download started')
        result=self.import_data(id_config)
        if result==True:
            _logger.info('Download ended')
        else:
            _logger.info('Download error')
            return False
        _logger.info('Synchronization started')
        result2=self.synchro_categ(id_config)
        if result2==True:
            _logger.info('products categories synchronization ended')
        else:
            _logger.info('products categories synchronization error')
            return False
        _logger.info('products synchronization started')
        result3=self.synchronisation(id_config)
        _logger.info(result3)
        if result3==True:
            _logger.info('products synchronization ended')
        else:
            _logger.info('products synchronization error')
            return False
            
        _logger.info('end synchronization')
        try :
            #self.write(cr,uid,id_config,{'date_cron' : time.strftime("%Y-%m-%d %H:%M:%S")})
            self.search([('id','=',id_config)]).write({'date_synchro' : time.strftime("%Y-%m-%d %H:%M:%S")})
        except:
            try :
                #self.write(cr,1,id_config,{'date_cron' : time.strftime("%Y-%m-%d %H:%M:%S")})
                self.search([('id','=',id_config)]).write({'date_synchro' : time.strftime("%Y-%m-%d %H:%M:%S")})
            except:pass
        _logger.info('Done')
        return True

    def synchro_categ(self,id_config):
        #config = self.read([id_config,'server_address','server_login','server_passwd','location_id','categorie_id','chemin','file_cat']) 
        config = id_config.read(['server_address','server_login','server_passwd','location_id','categorie_id','chemin','file_cat'])        
        categ = config[0]['categorie_id']
        categ = categ[0]
        file_cat=config[0]['file_cat']
        chm=str(config[0]['chemin'])
        listefich = os.listdir(chm+'/')    
        product_categ=self.env['product.category']
        product_public_category = self.env['product.public.category']
        compteur=0
        for i in listefich:
            
            if str(i) == 'price.zip':                     
                # specifying the zip file name 
                file_name1 = chm+'\\'+str(i)                         
                # opening the zip file in READ mode                      
                with ZipFile(file_name1, 'r') as zip: 
                    # printing all the contents of the zip file                                                        
                    zip.printdir()  
                    listOfFileNames = zip.namelist()
                    arr = os.listdir(chm)
                    
                    for file_itel in arr :
                                                                
                        if file_itel == file_cat :
                            f_name = chm+'\\'+str(file_itel)
                            os.remove(f_name)
                           
                    #extracting all the files 
                    
                    print('Extracting all the files now...')                       
                    zip.extractall(path=chm, members=None, pwd=None)
                    print('Done!') 

        listefich = os.listdir(chm+'/')
        for i in listefich:
                if str(i)==str(file_cat) :
                    fichier = open(chm+'/'+i,'rb')
                    fichiercsv = csv.reader(codecs.iterdecode(fichier, 'unicode_escape'),  delimiter="\t")
                    cat=cat1=[]                    
                    for ligne in fichiercsv:                        
                        if ligne[0] != 'ProdNr':
                            a17 = ligne[17]
                            b18 = ligne[18]
                            c13 = ligne[13]                            
                            ligne_un=product_categ.search([('code_categ_techdata','=',ligne[17]),('name','=',ligne[17])])
                            ligne_un_website=product_public_category.search([('code_categ_techdata','=',a17),('name','=',a17)]) 
                            if ligne_un:                                
                                ligne_trois=product_categ.search([('code_categ_techdata','=',ligne[13]),('name','=',ligne[13]),('parent_id','=',ligne_un[0].id)])                                                                
                            else:                                
                                ligne_trois=product_categ.search([('code_categ_techdata','=',ligne[13]),('name','=',ligne[13])])                                                                  
                            
                            if ligne_un_website:                                
                                ligne_trois_website=product_public_category.search([('code_categ_techdata','=',c13),('name','=',c13),('parent_id','=',ligne_un_website[0].id)])                                                                
                            else:
                                ligne_trois_website=product_public_category.search([('code_categ_techdata','=',c13),('name','=',c13)])                                  

                            if ligne_trois:                                
                                ligne_cinq=product_categ.search([('code_categ_techdata','=',ligne[18]),('name','=',ligne[18]),('parent_id','=',ligne_trois[0].id)])                                
                            else:                                
                                ligne_cinq=product_categ.search([('code_categ_techdata','=',ligne[18]),('name','=',ligne[18])])                                                  
                            _logger.info(compteur)
                            

                            if ligne_trois_website:                                
                                ligne_cinq_website=product_public_category.search([('code_categ_techdata','=',b18),('name','=',b18),('parent_id','=',ligne_trois_website[0].id)])
                            else:                                
                                ligne_cinq_website=product_public_category.search([('code_categ_techdata','=',b18),('name','=',b18)])                  

                            if not ligne_un:                                
                                ligne_un=product_categ.create({'name':ligne[17],'parent_id':categ,'code_categ_techdata':ligne[17]})                                                                
                                if ligne_un not in cat:
                                    cat.append(ligne_un)                               
                            else:
                                ligne_un=ligne_un[0]                                
                                product_categ.search([('id','=',ligne_un[0].id)]).write({'code_categ_techdata':ligne[17]})                                
                                if ligne_un not in cat:
                                    cat.append(ligne_un) 
                            if not ligne_un_website:
                                ligne_un_website=product_public_category.create({'name':a17,'code_categ_techdata':a17})                                                                
                                if ligne_un_website not in cat1:
                                    cat1.append(ligne_un_website)
                            else:
                                ligne_un_website=ligne_un_website[0]                                    
                                product_public_category.search([('id','=',ligne_un_website[0].id)]).write({'code_categ_techdata':a17})                                
                                if ligne_un_website not in cat1:
                                    cat1.append(ligne_un_website)    

                            if not ligne_trois:                                
                                ligne_trois=product_categ.create({'name':ligne[13],'parent_id':ligne_un.id,'code_categ_techdata':ligne[13]})                                
                                if ligne_trois not in cat:
                                    cat.append(ligne_trois)                                
                            else:
                                if product_categ.browse(ligne_trois[0].id).parent_id.id != ligne_un.id :
                                    product_categ.search([('id','=',ligne_trois[0].id)]).write({'parent_id':ligne_un[0].id,'code_categ_techdata':ligne[13]})                                    
                                else:                                  
                                    product_categ.search([('id','=',ligne_trois[0].id)]).write({'code_categ_techdata':ligne[13]})                                    
                                ligne_trois=ligne_trois[0]                                
                                if ligne_trois not in cat:
                                    cat.append(ligne_trois)

                            if not ligne_trois_website :                                
                                ligne_trois_website=product_public_category.create({'name':c13,'parent_id':ligne_un_website[0].id,'code_categ_techdata':c13})                                                                
                                if ligne_trois_website not in cat1:
                                    cat1.append(ligne_trois_website)
                            else:                                
                                if product_public_category.browse(ligne_trois_website[0].id).parent_id.id != ligne_un_website.id:
                                    product_public_category.search([('id','=',ligne_trois_website[0].id)]).write({'parent_id':ligne_un_website[0].id,'code_categ_techdata':c13})                                    
                                else:                                  
                                    product_public_category.search([('id','=',ligne_trois_website[0].id)]).write({'code_categ_techdata':c13})                                    
                                ligne_trois_website=ligne_trois_website[0]
                                if ligne_trois_website not in cat1:
                                    cat1.append(ligne_trois_website)  

                            if not ligne_cinq :                                
                                ligne_cinq = product_categ.create({'name':ligne[18],'parent_id':ligne_trois[0].id,'code_categ_techdata':ligne[18]})                                 
                                if ligne_cinq not in cat:
                                    cat.append(ligne_cinq)                                
                            else:
                                if product_categ.browse(ligne_cinq[0].id).parent_id.id != ligne_trois.id :
                                    product_categ.search([('id','=',ligne_cinq[0].id)]).write({'parent_id':ligne_trois[0].id,'code_categ_techdata':ligne[18]})                                   
                                else:                              
                                    product_categ.search([('id','=',ligne_cinq[0].id)]).write({'code_categ_techdata':ligne[18]})                                    
                                if ligne_cinq not in cat:
                                    cat.append(ligne_cinq)                                

                            if not ligne_cinq_website :                                
                                ligne_cinq_website = product_public_category.create({'name':b18,'parent_id':ligne_trois_website[0].id,'code_categ_techdata':b18})                                 
                                if ligne_cinq_website not in cat1:
                                    cat1.append(ligne_cinq_website)
                            else:                                
                                if product_public_category.browse(ligne_cinq_website[0].id).parent_id.id != ligne_trois_website.id:                                    
                                    product_public_category.search([('id','=',ligne_cinq_website[0].id)]).write({'parent_id':ligne_trois_website[0].id,'code_categ_techdata':b18})                                    
                                else:                                                                  
                                    product_public_category.search([('id','=',ligne_cinq_website[0].id)]).write({'code_categ_techdata':b18})                                    
                                if ligne_cinq_website not in cat1:
                                    cat1.append(ligne_cinq_website) 
                        compteur+=1
                    fichier.close()
                    idss=product_categ.search([('code_categ_techdata','!=',False)])                    
                    tab=[]                 
                    for i in idss:
                        if i not in cat:
                            tab.append(i)
                            product_categ.search([('id','=',i.id)]).write({'code_categ_techdata':'-1'})
                    idsss=product_public_category.search([('code_categ_techdata','!=',False)])
                    tab1=[]
                    for i in idsss:
                        if i not in cat1:                            
                            tab1.append(i)
                            product_public_category.search([('id','=',i.id)]).write({'code_categ_techdata':'-1'})
        return True

    