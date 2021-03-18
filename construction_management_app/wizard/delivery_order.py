# -*- coding: utf-8 -*-

import time

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta

class PickingWizard(models.TransientModel):
    _name = 'delivery.order.wizard'

    product_line_ids = fields.One2many(
        'delivery.product.lines',
        'product_line_id',
        'Product Lines'
    )

    @api.model
    def default_get(self, fields):
        rec = super(PickingWizard, self).default_get(fields)
        context = dict(self._context or {})
        active_model = context.get('active_model')
        active_ids = context.get('active_ids')
        material_req = self.env[active_model].browse(active_ids)
        vals = []
        for line in material_req.material_req_line_ids:
            if line.product_id.type == 'product':
                vals.append((0,0,{'product_id': line.product_id.id,
                                 'quantity': line.quantity,
                                  }))
        rec.update({'product_line_ids': vals})
        return rec

    #@api.multi
    def _prepare_delivery_order(self):
        self.ensure_one()
        material_req_obj = self.env['construction_management_app.material_req'].browse(self._context.get('active_ids', []))



        delivery_order_vals = {
            'picking_type_id': self.env['stock.picking.type'].search([('code', '=', 'outgoing')], order="id asc", limit=1).id,
            'project_id': material_req_obj.project_id.id,
            'material_reqisition_id': material_req_obj.id,
            'analytic_account_id': material_req_obj.analytic_account_id.id,
            'task_id': material_req_obj.task_id.id,
            'company_id': self.env.company.id,
            'location_id': self.env['stock.location'].search([('usage', '=', 'internal')], order="id asc", limit=1).id,
            'location_dest_id': self.env['stock.location'].search([('usage', '=', 'customer')], order="id asc", limit=1).id
        }
        return delivery_order_vals

    #@api.multi
    def create_delivery_order(self):

        material_req = self.env['construction_management_app.material_req'].browse(self._context.get('active_ids', []))
        picking = self.env['stock.picking']
        picking_line = self.env['stock.move']

        picking_ids = []

        delivery_order = self._prepare_delivery_order()
        picking = picking.sudo().create(delivery_order)

        for line in self.product_line_ids:
            if line.product_id.type == 'product':
                picking.move_ids_without_package =  ([(0, 0, {
                         'product_id': line.product_id.id,
                         'name':line.product_id.name,
                         'quantity_done': line.quantity,
                         'company_id': self.env.company.id,
                         'product_uom': line.product_id.uom_id.id,
                         'location_id': self.env['stock.location'].search([('usage', '=', 'internal')], order="id asc", limit=1).id,
                         'location_dest_id': self.env['stock.location'].search([('usage', '=', 'customer')], order="id asc", limit=1).id
                         })])
        picking_ids.append(picking.id)

        for line in material_req[0].picking_ids:
            picking_ids.append(line.id)

        material_req[0].picking_ids = picking_ids

        action = self.env.ref('stock.stock_picking_action_picking_type').read()[0]
        action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
        action['res_id'] = picking.id
        return action


class PickingProductLines(models.TransientModel):
    _name = 'delivery.product.lines'

    material_reqisition_id = fields.Many2one('construction_management_app.material_req', string='Material Requistion')
    product_id = fields.Many2one('product.product', string="Product")
    quantity = fields.Float('Quantity', default=1)
    product_line_id = fields.Many2one('delivery.order.wizard')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for r in self:
            if r.product_id:
                r.rate = r.product_id.lst_price
                r.name = r.product_id.name

    @api.depends('quantity', 'rate')
    def _compute_price_subtotal(self):
        for r in self:
            r.price_subtotal = 0
            if r.quantity and r.rate:
                r.price_subtotal = r.quantity * r.rate
    @api.model
    def create(self, vals):
        result = super(PickingProductLines, self).create(vals)
        # result._onchange_product_id()
        return result
