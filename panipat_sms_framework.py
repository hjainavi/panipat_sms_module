# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.exceptions import except_orm
from datetime import datetime
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
import requests
import re
import pytz
import logging
import time

_logger = logging.getLogger(__name__)


class panipat_sms_framework(models.Model):
    _name = "panipat.sms.framework"
    _rec_name="sender_name"
    
    apikey=fields.Char(string="Api Key")
    credits_left=fields.Integer(string="Balance Left")
    sender_name=fields.Char(string="Sender Names")
    templates=fields.One2many(comodel_name='panipat.sms.framework.templates', inverse_name="framework_id", string="Pre-Approved Messages")

    '''
    @api.model
    def create(self,vals):
        ids=self.search([])
        if ids and len(ids)>=1:
            raise except_orm(_('Error!'), _('Cannot create more than one settings for sms'))
        return super(panipat_sms_framework, self).create(vals)
    '''

    @api.multi
    def getbalance(self):
        #print "------------------------090909090909090",self._context
        api_endpoint= "http://api.textlocal.in/balance/"
        api_key=self.apikey
        data={'apiKey':api_key}
        try:
            resp = requests.post(url=api_endpoint,data=data)
            j = resp.json()
            print resp.text
            print j['status']
            if j['status']=='success':
                self.credits_left=j['balance']['sms']
            elif "params" not in self._context:
                pass
            else:
                raise except_orm(_('Error!'), _('Please Contact administrator \n %s'%(str(resp.text))))    
        except requests.exceptions.RequestException as e:  # This is the correct syntax
            if "params" not in self._context:
                pass # This is to not raise error if function run on install of module
            else:
                raise except_orm(_('Error!'), _('Please check internet \nPlease Contact administrator \n %s'%(e)))

    @api.multi
    def get_sender_names(self):
        api_endpoint= "http://api.textlocal.in/get_sender_names/"
        api_key=self.apikey
        data={'apiKey':api_key}
        try:
            resp = requests.post(url=api_endpoint,data=data)
            j = resp.json()
            print resp.text
            print j['status']
            if j['status']=='success':
                self.sender_name=j['default_sender_name']
            elif "params" not in self._context:
                pass
            else:
                raise except_orm(_('Error!'), _('Please Contact administrator \n %s'%(str(resp.text))))    
        except requests.exceptions.RequestException as e:  # This is to not raise error if function run on install of module
            if "params" not in self._context:
                pass
            else:
                raise except_orm(_('Error!'), _('Please check internet \nPlease Contact administrator \n %s'%(e)))


    @api.multi
    def get_templates(self):
        api_endpoint= "http://api.textlocal.in/get_templates/"
        api_key=self.apikey
        data={'apiKey':api_key}
        try:
            resp = requests.post(url=api_endpoint,data=data)
            j = resp.json()
            print resp.text
            print j['status']
            if j['status']=='success':
                existing_template_ids=self.env['panipat.sms.framework.templates'].search([])
                if existing_template_ids:
                    # next few lines to retain existing forwardto and forwardto_employees when templates is downloaded from api
                    title_forwardto={}
                    title_forwardto_employees={}
                    for rec in existing_template_ids:
                        title_forwardto[rec.title]=rec.forwardto
                        title_forwardto_employees[rec.title]=rec.forwardto_employees
                    existing_template_ids.unlink()

                for temp in j['templates']:
                    vals={}
                    vals['title']=temp['title']
                    vals['msg_content']=temp['body']
                    vals['framework_id']=self.id
                    vals['internal_id']=temp['id']
                    vals['senderName']=temp['senderName']
                    vals['dnd']=temp['isMyDND']
                    rec_temp_id=self.env['panipat.sms.framework.templates'].create(vals)

                    forward_ids=map(int,title_forwardto.get(temp['title'],False) or [] )
                    forward_employees_ids=map(int,title_forwardto_employees.get(temp['title'],False) or [] )
                    rec_temp_id.write({'forwardto':[(6,0,forward_ids)],'forwardto_employees':[(6,0,forward_employees_ids)]})

            elif "params" not in self._context:
                pass # This is to not raise error if function run on install of module
            else:
                raise except_orm(_('Error!'), _('Please check internet \nPlease Contact administrator \n %s'%(str(resp.text))))    
        except requests.exceptions.RequestException as e:  # This is the correct syntax
            if "params" not in self._context:
                pass
            else:
                raise except_orm(_('Error!'), _('Please check internet \nPlease Contact administrator \n %s'%(e)))
class panipat_sms_framework(models.Model):
    _name = "panipat.sms.framework.templates"
    _rec_name="title"

    title=fields.Char(string="Internal Title")
    msg_content=fields.Text(string="Message Content")
    internal_id=fields.Integer(string="id")
    senderName=fields.Char(string="senderName")
    dnd=fields.Char(string="isMyDND")
    framework_id=fields.Many2one(comodel_name='panipat.sms.framework',string="framework",required=True)
    forwardto=fields.Many2many(comodel_name='res.partner',string="Forward To Contacts")
    forwardto_employees=fields.Many2many(comodel_name='hr.employee',string="Forward To Employees")

class panipat_sms_send(models.TransientModel):
    _name="panipat.sms.send"

    partners=fields.Many2many(comodel_name='res.partner',string="Contacts")
    partner_numbers=fields.Char("Contact Nos.")
    recipients=fields.Text("Other Recipients")
    employee=fields.Many2many(comodel_name='hr.employee',string="Employees")
    employee_numbers=fields.Char("Employee Numbers")


    @api.onchange("partners")
    def onchange_partners(self):
        partner_numbers=[]
        for rec in self.partners:
            if rec.mobile:
                try:
                    int(rec.mobile)
                except ValueError:
                    raise except_orm(_('Error!'), _('Each Contact Number should be 10 digits only. please check the contact ""%s""'%(rec.name)))
                if len(str(int(rec.mobile)))!=10:
                    raise except_orm(_('Error!'), _('Each Contact Number should be 10 digits only. please check the contact ""%s""'%(rec.name)))
                #print n
                partner_numbers.append(str(rec.mobile))
            else:
                partner_numbers.append("-empty-")
        self.partner_numbers=",".join(partner_numbers)

    @api.onchange("employee")
    def onchange_employee(self):
        employee_numbers=[]
        for rec in self.employee:
            if rec.work_phone:
                try:
                    int(rec.work_phone)
                except ValueError:
                    raise except_orm(_('Error!'), _('Each Employee Work Mobile should be 10 digits only. please check the contact ""%s""'%(rec.name)))
                if len(str(int(rec.work_phone)))!=10:
                    raise except_orm(_('Error!'), _('Each Employee Work Mobile should be 10 digits only. please check the contact ""%s""'%(rec.name)))
                #print n
                employee_numbers.append(str(rec.work_phone))
            else:
                employee_numbers.append("-empty-")
        self.employee_numbers=",".join(employee_numbers)

