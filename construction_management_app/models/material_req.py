# -*- coding: utf-8 -*-

from odoo import models, fields, api

# class MaterialRequisition(models.Model):
#     _name = "construction_management_app.material_requisition"
#     _description = "Material Requisition"
#
#     name = fields.Char(string='Number', readonly=True, copy=False, default='New')
#
#     task_user_id = fields.Many2one('res.users', related='task_id.user_id', string='Task / Job Order User')
#
#     task_id = fields.Many2one('project.task', string='Task / Job Order')
#
#     project_id = fields.Many2one(
#         'project.project',
#         string='Construction Project',
#     )
#
#     type = fields.Selection([
#         ('plan', 'Plan'),
#         ('requistion', 'Requistion')], 'Type')
#
#     analytic_account_id = fields.Many2one(
#         'account.analytic.account',
#         string='Analytic Account',
#     )
#
#     material_req_line_ids = fields.One2many('construction_management_app.material_req_line', 'material_reqisition_id')
#
#     @api.onchange('project_id')
#     def _onchange_project_id(self):
#         res = {}
#         for r in self:
#             if r.project_id:
#                 # task domain
#                 res['domain'] = {'task_id': [('project_id', '=', r.project_id.id)]}
#
#                 #get analytic_account_id from parent project_id
#                 if r.project_id.is_a_sup_project:
#                     project_obj = self.env['project.project']
#                     parent_proj = project_obj.search([('subtask_project_id', '=', r.project_id.id)], limit=1)
#                     r.analytic_account_id = parent_proj.analytic_account_id.id if parent_proj.analytic_account_id else False
#                 elif not r.project_id.is_a_sup_project:
#                     r.analytic_account_id = r.project_id.analytic_account_id.id if r.project_id.analytic_account_id else False
#         return res
#
#     @api.model
#     def create(self, vals):
#         vals['name'] = self.env['ir.sequence'].next_by_code('mgs_billing.meter_reading')
#         result = super(MeterReading, self).create(vals)
#
#         return result
#
# class MaterialRequisitionLine(models.Model):
#     _name = "construction_management_app.material_req_line"
#     _description = "Material Requisition Line"
#
#     material_reqisition_id = fields.Many2one('construction_management_app.material_requisition', string='Material Requistion')
#     product_id = fields.Many2one('product.product', string="Product")
#     name = fields.Char(string="Description", required=True)
#     quantity = fields.Float('Quantity', default=1)
#     rate = fields.Float('Unit Price')
#     price_subtotal = fields.Monetary(string="Total", compute="_compute_price_subtotal")
#     currency_id = fields.Many2one('res.currency', 'Currency', required=True, \
#                                   default=lambda self: self.env.user.company_id.currency_id.id)
#
#     @api.onchange()
#     def _onchange_product_id(self):
#         for r in self:
#             if r.product_id:
#                 r.rate = r.product_id.lst_price
#                 r.name = r.product_id.name
#
#     @api.depends('quantity', 'rate')
#     def _compute_price_subtotal(self):
#         for r in self:
#             if r.quantity and r.rate:
#                 r.price_subtotal = r.quantity * r.rate
