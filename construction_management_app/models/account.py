# -*- coding: utf-8 -*-

from odoo import models, fields, api

class Invoice(models.Model):
    _inherit = "account.move"

    project_id = fields.Many2one('project.project', string='Project')
    task_id = fields.Many2one('project.task', string='Task')
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
    )
    material_reqisition_id = fields.Many2one('construction_management_app.material_req', string='Material Requistion')

    @api.onchange('project_id')
    def _onchange_project_id_(self):
        for r in self:
            if r.project_id:
                r.analytic_account_id = r.project_id.analytic_account_id.id

    # @api.model
    # def create(self, vals):
    #     invoice = super(Invoice, self).create(vals)
    #     invoice._onchange_project_id_material_req_id()
    #     return invoice
# 
# class InvoiceLine(models.Model):
#     _inherit = "account.move.line"
#
#     @api.onchange('move_id')
#     def _onchange_move_id(self):
#         for r in self:
#             r.analytic_account_id = r.move_id.analytic_account_id.id
