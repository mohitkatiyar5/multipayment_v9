import time
from openerp.osv import osv
from openerp.report import report_sxw
from datetime import date, datetime
from dateutil import relativedelta
import json
import re
import requests
import openerp.addons.decimal_precision as dp
from openerp.tools import amount_to_text_en


class custom_account_payment_report(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(custom_account_payment_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
                'convert':self.convert,
                'get_amount':self.get_amount,
                'get_total_amount':self.get_total_amount,
                'get_user':self.get_user,
            })
    total_amt =0.0
    paid_amt = 0.0
    def get_amount(self,amt):
           
        if amt:
            amt = amt
        else:
            amt = 0.0
        self.total_amt +=  amt 
        return '{:,.2f}'.format(amt)
    
    def get_total_amount(self,line,amount):
        total_amount = 0.0
        if line:
            total_amount = self.total_amt
        else:
            total_amount = amount
            self.paid_amt = amount
        return '{:,.2f}'.format(total_amount)
        
    def convert(self,allocated_amt,amount,currency_id):
        if allocated_amt:
            amount= allocated_amt
        else:
            amount = amount
        amt_en =  amount_to_text_en.amount_to_text(amount,'en',currency_id.name) + ' ' + 'Only '
        amt_en = amt_en.replace(',',' ')
        amt_en = amt_en.replace('-',' ')
        if currency_id.name == 'AED':
            amt_en = amt_en.replace('Cent','Fil')
        return amt_en
    
    def get_user(self):
        temp = self.pool.get('res.users').browse(self.cr,self.uid,self.uid)
        return temp.name



class custom_account_payment_report_qweb(osv.AbstractModel):
    _name = 'report.account_payment.account_custom_payment_report_id'
    _inherit = 'report.abstract_report'
    _template = 'account_payment.account_custom_payment_report_id'
    _wrapped_report_class = custom_account_payment_report