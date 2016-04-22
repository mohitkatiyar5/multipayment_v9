from openerp.osv import fields,osv
from datetime import datetime,timedelta
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp.tools.translate import _
from openerp import api
from openerp import models
from openerp.exceptions import UserError, ValidationError

class custom_account_payment(osv.osv):
    _name = 'custom.account.payment'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order = "id desc,payment_date desc"
    
    def _get_allocated_amt(self,cr,uid,ids,name,args=None,context=None):
        res = {}
        for temp in self.browse(cr,uid,ids):
            sum = 0
            for inv_line in temp.line_ids:
                sum += inv_line.allocated_amt
            res[temp.id] = sum    
        return res
    
    def _get_total_amount(self,cr,uid,ids,name,args=None,context=None):
        res = {}
        for temp in self.browse(cr,uid,ids):
            sum = 0
            for inv_line in temp.line_ids:
                sum += inv_line.amount
            res[temp.id] = sum    
        return res
    
    def _get_total_due_amount(self,cr,uid,ids,name,args=None,context=None):
        res = {}
        for temp in self.browse(cr,uid,ids):
            sum = 0
            for inv_line in temp.line_ids:
                sum += inv_line.residual_amount
            res[temp.id] = sum    
        return res
    
    def _get_write_off_amt(self,cr,uid,ids,name,args=None,context=None):
        res = {}
        for temp in self.browse(cr,uid,ids):
            sum = 0
            res[temp.id] = temp.amount - temp.total_allocated_amt    
        return res
    
    def _get_default_company(self, cr, uid, context=None):
        company_id = self.pool.get('res.users')._get_company(cr, uid, context=context)
        if not company_id:
            raise osv.except_osv(_('Error!'), _('There is no default company for the current user!'))
        return company_id
    
    _columns={
              'name':fields.char('Name',track_visibility='onchange'),
              'payment_type':fields.selection([('outbound','Send Money'),('inbound','Receive Money')],'Payment Type',track_visibility='onchange'),
              'partner_type':fields.selection([('customer','Customer'),('supplier','Vendor')],'Partner Type',track_visibility='onchange'),
              'partner_id':fields.many2one('res.partner','Partner',track_visibility='onchange'),
              'journal_id':fields.many2one('account.journal','Payment Method'),
              'amount':fields.float('Paid Amount',track_visibility='onchange'),
              'line_ids':fields.one2many('line.cr.dr','payment_id','Voucher Lines'),
              'total_amount':fields.function(_get_total_amount,type="float", string="Total Amount"),
              'total_due_amount':fields.function(_get_total_due_amount,type="float", string="Total Due Amount"),
              'state':fields.selection([('draft','Draft'),('posted','Posted'),('cancel','Cancel')],'State',track_visibility='onchange'),
              'payment_date':fields.date('Payment Date',track_visibility='onchange'),
              'communication':fields.char('Communication'),
              'has_invoices':fields.boolean('Has Boolean'),
              'total_allocated_amt':fields.function(_get_allocated_amt,type="float", string="Total Allocated Amount"),
              'account_payment_id':fields.many2one('account.payment','Payment'),
              'write_off_amt':fields.function(_get_write_off_amt,type="float", string="Write Off Amount"),
              'currency_id':fields.many2one('res.currency','Currency',track_visibility='onchange'),
              'counter_part_account_id':fields.many2one('account.account',string="Counter Account",help="Counter Part Account For Advance Payment"),
              'payment_option':fields.selection([
                                           ('without_writeoff', 'Keep Open'),
                                           ('with_writeoff', 'Reconcile Payment Balance'),
                                           ], 'Payment Difference', required=True, readonly=True, states={'draft': [('readonly', False)]}, help="This field helps you to choose what you want to do with the eventual difference between the paid amount and the sum of allocated amounts. You can either choose to keep open this difference on the partner's account, or reconcile it with the payment(s)"),
              
              'company_id':fields.many2one('res.company','Company'),
              }
    
    _defaults = {'state':'draft',
                 'payment_date':fields.datetime.now(),
                 'currency_id':133,
                 'payment_option':'without_writeoff',
#                  'company_id':_get_default_company,
                 'company_id':lambda self, cr, uid, ctx: self.pool.get('res.company')._company_default_get(cr, uid, 'custom.account.payment', context=ctx),
                 
                 }
    
    def validate_payment(self,cr,uid,ids,context=None):
        for custom_payment in self.browse(cr,uid,ids):
            if custom_payment.payment_type == 'inbound':
               payment_method_id = 1
            elif custom_payment.payment_type == 'outbound':
               payment_method_id = 2  
            else:
               payment_method_id = 3 
                
                    
            diff_payment_id = False
            for val in custom_payment.line_ids:
                vals = {'invoice_ids':[(6,0,[val.invoice_id.id])],
                        'payment_type':custom_payment.payment_type,
                        'partner_type':custom_payment.partner_type,
                        'partner_id':custom_payment.partner_id.id,
                        'journal_id':custom_payment.journal_id.id,
                        'destination_journal_id':custom_payment.journal_id.id,
                        'amount':val.allocated_amt,
                        'currency_id':custom_payment.currency_id.id,
                        'payment_date':custom_payment.payment_date,
                        'communication':custom_payment.communication,
                        'payment_method_id':payment_method_id,
                        'name':custom_payment.name
                        }    
            
                payment_id = self.pool.get('account.payment').create(cr,uid,vals)     
                self.pool.get('account.payment').post(cr,uid,[payment_id],context=None)
                cr.execute("update line_cr_dr set account_payment_id = '"+str(payment_id)+"',state='"+str('posted')+"' where id = '"+str(val.id)+"'")
                
            if (custom_payment.amount - custom_payment.total_allocated_amt):
                diff_payment_id = self.pool.get('account.payment').create(cr,uid,{'payment_type':custom_payment.payment_type,
                                                                             'partner_type':custom_payment.partner_type,
                                                                             'partner_id':custom_payment.partner_id.id,
                                                                             'journal_id':custom_payment.journal_id.id,
                                                                             'destination_journal_id':custom_payment.journal_id.id,
                                                                             'amount':custom_payment.write_off_amt,
                                                                             'currency_id':custom_payment.currency_id.id,
                                                                             'payment_date':custom_payment.payment_date,
                                                                             'communication':custom_payment.communication,
                                                                             'payment_method_id':payment_method_id,
                                                                             'name':custom_payment.name,
                                                                             'counter_part_account_id':custom_payment.counter_part_account_id and custom_payment.counter_part_account_id.id or False  
                                                                            })  
                   
                self.pool.get('account.payment').post(cr,uid,[diff_payment_id],context=None)     
            self.write(cr,uid,ids,{'state':'posted','account_payment_id':diff_payment_id})
            return True
    
    
    def cancel_payment(self,cr,uid,ids,context=None):
        for custom_payment in self.browse(cr,uid,ids):
            payment_ids = []
            if custom_payment.account_payment_id:
               payment_ids.append(custom_payment.account_payment_id.id)
               self.pool.get('account.payment').cancel(cr,uid,[custom_payment.account_payment_id.id],context=None)
            for val in custom_payment.line_ids:
                if val.account_payment_id:
                   payment_ids.append(val.account_payment_id.id) 
                   self.pool.get('account.payment').cancel(cr,uid,[val.account_payment_id.id],context=None)
            cr.execute("update custom_account_payment set state='"+str('cancel')+"' where id = '"+str(custom_payment.id)+"'") 
            if payment_ids:
               payment_ids.append(1.5) 
               cr.execute("delete from account_payment where id in "+str(tuple(payment_ids))+"")
            cr.execute("update line_cr_dr set state='"+str('cancel')+"' where payment_id = '"+str(custom_payment.id)+"'")
        return True
    
    def set_to_draft(self,cr,uid,ids,context=None):
        for custom_payment in self.browse(cr,uid,ids):
            cr.execute("delete from line_cr_dr where payment_id = '"+str(custom_payment.id)+"'")
            cr.execute("update custom_account_payment set amount ='"+str(0)+"',has_invoices ="+str(False)+",state ='"+str('draft')+"',counter_part_account_id = Null where id = '"+str(custom_payment.id)+"'")
        return True
    
    def get_payment_type(self,cr,uid,ids,payment_type,context=None):
        res = {}
        if payment_type == 'inbound':
            res['value'] = {'partner_type':'customer'}
        else:
            res['value'] = {'partner_type':'supplier'}    
        return res
    
    def get_partner_type(self,cr,uid,ids,partner_type,context=None):
        res = {}
        if partner_type == 'customer':
            customer_ids = self.pool.get('res.partner').search(cr,uid,[('customer','=',True)])
            res['domain'] = {'partner_id':[('id','in',customer_ids)]}
        else:
            supplier_ids = self.pool.get('res.partner').search(cr,uid,[('supplier','=',True)])
            res['domain'] = {'partner_id':[('id','in',supplier_ids)]}    
        return res
    
    def create(self,cr,uid,vals,context=None):
        if vals.get('payment_type') == 'inbound':
            temp = self.pool.get('ir.sequence').get(cr, uid, 'customer.payment') or '/'
        elif vals.get('payment_type') == 'outbound':
            temp = self.pool.get('ir.sequence').get(cr, uid, 'supplier.payment') or '/'
        print"===========vals['payment_date']==========",vals['payment_date']
        date = datetime.strptime(vals['payment_date'],"%Y-%m-%d").strftime("%Y")
        print"=====date=======",date
        vals['name'] = temp + '/' + str(date)
        res = super(custom_account_payment,self).create(cr,uid,vals,context=None)          
        return res
    
    @api.multi
    def button_journal_entries(self):
        payment_ids = []
        payment_ids = [val.account_payment_id.id for val in self.line_ids]
        if self.account_payment_id:
            payment_ids.append(self.account_payment_id.id)   
        
        return {
            'name': _('Journal Items'),
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'account.move.line',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('payment_id', 'in', payment_ids)],
        }
        
    @api.multi
    def button_invoices(self):
        invoice_ids = [val.invoice_id.id for val in self.line_ids]
        return {
            'name': _('Paid Invoices'),
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'account.invoice',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', invoice_ids)],
        }  
        
          
class account_payment(osv.osv):
    _inherit = "account.payment"
    
    _columns={
              'counter_part_account_id':fields.many2one('account.account',string="Counter Account",help="Counter Part Account For Advance Payment"),          
              }
    
    def _create_payment_entry(self, amount):
        """ Create a journal entry corresponding to a payment, if the payment references invoice(s) they are reconciled.
            Return the journal entry.
        """
        aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
        debit, credit, amount_currency = aml_obj.with_context(date=self.payment_date).compute_amount_fields(amount, self.currency_id, self.company_id.currency_id)

        move = self.env['account.move'].create(self._get_move_vals())

        #Write line corresponding to invoice payment
        counterpart_aml_dict = self._get_shared_move_line_vals(debit, credit, amount_currency, move.id, False)
        counterpart_aml_dict.update(self._get_counterpart_move_line_vals(self.invoice_ids))
        counterpart_aml_dict.update({'currency_id': self.currency_id != self.company_id.currency_id and self.currency_id.id or False})
        if not self.invoice_ids and self.counter_part_account_id:
           counterpart_aml_dict.update({'account_id':self.counter_part_account_id.id}) 
        counterpart_aml = aml_obj.create(counterpart_aml_dict)
        
        #Reconcile with the invoices
        if self.payment_difference_handling == 'reconcile':
            self.invoice_ids.register_payment(counterpart_aml, self.writeoff_account_id, self.journal_id)
        else:
            self.invoice_ids.register_payment(counterpart_aml)

        #Write counterpart lines
        liquidity_aml_dict = self._get_shared_move_line_vals(credit, debit, -amount_currency, move.id, False)
        liquidity_aml_dict.update(self._get_liquidity_move_line_vals(-amount))
        aml_obj.create(liquidity_aml_dict)

        move.post()
        return move     
    
        