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

class SaleOrder(models.Model):
    _inherit = "sale.order"

        