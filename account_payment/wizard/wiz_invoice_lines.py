from openerp.osv import fields,osv
from datetime import datetime,timedelta
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp.tools.translate import _
from openerp import api

class wiz_payment(osv.osv):
    _name = 'wiz.payment'
    
    
    _columns={
              'name':fields.char('Name'),
              'total_amount':fields.float('Total Amount'),
              'invoice_lines':fields.one2many('line.cr.dr','wiz_payment_id','Invoice Lines'),
              'total_due_amount':fields.float('Total Due Amount'),
              }
    
    def default_get(self,cr,uid,fields,context=None):
        res={}
        payment_obj = self.pool.get(context.get('active_model'))
        active_id = context.get('active_id')
        
        payment = payment_obj.browse(cr,uid,active_id)
        payment_invoice_lines = [val.invoice_id.id for val in payment.line_ids]
        lst = []
        sum_amt = 0
        sum_due_amt = 0
        invoice_ids = self.pool.get('account.invoice').search(cr,uid,[('partner_id','=',payment.partner_id.id),('state','=','open'),('id','not in',payment_invoice_lines)])
        if invoice_ids:
           invoices = self.pool.get('account.invoice').browse(cr,uid,invoice_ids)
           for val in invoices:
               sum_amt += val.amount_total
               sum_due_amt += val.residual
               lst.append((0,False,{'invoice_id':val.id,
                               'amount':val.amount_total,
                               'residual_amount':val.residual,
                               'state':'draft',
                               })) 
        res = {'invoice_lines':lst,'total_amount':sum_amt,'total_due_amount':sum_due_amt}
        return res
    
    
    def get_allocated_invoice_lines(self,cr,uid,ids,context=None):
        payment_obj = self.pool.get(context.get('active_model'))
        active_ids = context.get('active_ids')
        
        wiz_pay = self.browse(cr,uid,ids,context=None)
        lst = []
        lst = [(4,inv_line.id) for inv_line in wiz_pay.invoice_lines if inv_line.allocated_amt]
        if lst:
            payment_obj.write(cr,uid,active_ids,{'line_ids':lst,
                                                 'has_invoices':True,
                                                 })
        return True
    
class line_cr_dr(osv.osv):
    _name='line.cr.dr'
    
    _columns={
              'invoice_id':fields.many2one('account.invoice','Invoice'),
              'amount':fields.float('Amount'),
              'residual_amount':fields.float('Due Amount'),
              'reconcile':fields.boolean('Reconcile'),
              'allocated_amt':fields.float('Allocated Amount'),
              'wiz_payment_id':fields.many2one('wiz.payment','Payment'),
              'payment_id':fields.many2one('custom.account.payment','Payment'),
              'account_payment_id':fields.many2one('account.payment','Payment'),
              'state':fields.selection([('draft','Draft'),('posted','Posted'),('cancel','Cancel')],'State'),
              }  
    
    def get_reconciled_amt(self,cr,uid,ids,residual_amount,reconciled,context=None):
        res = {}
        if reconciled:
            res['value'] = {'allocated_amt':residual_amount}
        return res  

