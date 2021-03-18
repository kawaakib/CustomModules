# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError

class MaterialPlanning(models.Model):
    _name = 'material.plan'

    @api.onchange('product_id')
    def onchange_product_id(self):
        result = {}
        if not self.product_id:
            return result
        self.product_uom = self.product_id.uom_po_id or self.product_id.uom_id
        self.description = self.product_id.name

    product_id = fields.Many2one(
        'product.product',
        string='Product'
    )
    description = fields.Char(
        string='Description'
    )
    product_uom_qty = fields.Integer(
        'Quantity',
        default=1.0
    )
    product_uom = fields.Many2one(
        'uom.uom',
        'Unit of Measure'
    )
    material_task_id = fields.Many2one(
        'project.task',
        'Material Plan Task'
    )


class ConsumedMaterial(models.Model):
    _name = 'consumed.material'

    @api.onchange('product_id')
    def onchange_product_id(self):
        result = {}
        if not self.product_id:
            return result
        self.product_uom = self.product_id.uom_po_id or self.product_id.uom_id
        self.description = self.product_id.name


    product_id = fields.Many2one(
        'product.product',
        string='Product'
    )
    description = fields.Char(
        string='Description'
    )
    product_uom_qty = fields.Integer(
        'Quantity',
        default=1.0
    )
    product_uom = fields.Many2one(
        'uom.uom',
        'Unit of Measure'
    )
    consumed_task_material_id = fields.Many2one(
        'project.task',
        'Consumed Material Plan Task'
    )

    start_time = fields.Datetime('Start Time')
    datetime_deadline = fields.Datetime('Deadline')
    completed_date = fields.Datetime('Completed Date')

class ProjectTask(models.Model):
    _inherit = 'project.task'

    # @api.multi
    @api.depends('picking_ids.move_lines')
    def _compute_stock_picking_moves(self):
        for rec in self:
            rec.ensure_one()
            for picking in rec.picking_ids:
                rec.move_ids = picking.move_lines.ids

    def total_stock_moves_count(self):
        for task in self:
            task.stock_moves_count = len(task.move_ids)

    def _compute_notes_count(self):
        for task in self:
            task.notes_count = len(task.notes_ids)

    picking_ids = fields.One2many(
        'stock.picking',
        'task_id',
        'Stock Pickings'
    )
    move_ids = fields.Many2many(
        'stock.move',
        compute='_compute_stock_picking_moves',
        store=True,
    )
    material_plan_ids = fields.One2many(
        'material.plan',
        'material_task_id',
        'Material Plannings'
    )
    consumed_material_ids = fields.One2many(
        'consumed.material',
        'consumed_task_material_id',
        'Consumed Materials'
    )
    stock_moves_count = fields.Integer(
        compute='total_stock_moves_count',
        string='# of Stock Moves',
        store=True,
    )
    parent_task_id = fields.Many2one(
        'project.task',
        string='Parent Task',
        readonly=True
    )
    child_task_ids = fields.One2many(
        'project.task',
        'parent_task_id',
        string='Child Tasks'
    )
    notes_ids = fields.One2many(
        'note.note',
        'task_id',
        string='Notes',
    )
    planning_ids = fields.One2many(
        'construction_management_app.material_conceptions',
        'task_id',
        string='Material Requisition',
    ) #

    material_req_ids = fields.One2many('construction_management_app.material_req', 'task_id')
    m_req_count = fields.Integer(
        compute='_m_req_count',
        string="M.REQ",
        store=True,
    )
    bill_ids = fields.One2many('account.move', 'task_id', string='Bills', domain=[('move_type', '=', 'in_invoice')])
    bill_count = fields.Integer(
        compute='_bill_count',
        string="Bills",
        store=True,
    )

    # material_req_ids = fields.One2many(
    #     'construction_management_app.material_req_line',
    #     'task_id',
    #     string='Material Requisition',
    #     domain=[('material_req_type', '=', 'requistion')]
    # )
    notes_count = fields.Integer(
        compute='_compute_notes_count',
        string="Notes"
    )
    date_start = fields.Datetime(string='Starting Date', default=fields.Datetime.now, index=True, copy=False)
    deadline = fields.Datetime(string='Deadline Date', index=True, copy=False)
    total_consumed = fields.Float(string="Total Consumed", compute="_compute_total_consumed", store=True)
    total_planned = fields.Float(string="Total Planned", compute="_compute_total_planned", store=True)

    @api.depends('bill_ids')
    def _bill_count(self):
        for rec in self:
            rec.bill_count = len(rec.bill_ids)

    @api.depends('material_req_ids')
    def _m_req_count(self):
        for rec in self:
            rec.m_req_count = len(rec.material_req_ids)

    def bill_create(self):
        action = self.env.ref('account.action_move_in_invoice_type')
        result = action.read()[0]

        result['context'] = {'default_move_type': 'in_invoice'}

        # result['context']['account_analytic_id'] = self.analytic_account_id.id

        journal_domain = [
            ('type', '=', 'purchase'),
            ('company_id', '=', self.company_id.id),
            # ('currency_id', '=', self.currency_id.id),
        ]

        default_journal_id = self.env['account.journal'].search(
            journal_domain, limit=1)

        if default_journal_id:
            result['context']['default_journal_id'] = default_journal_id.id

        result['context']['default_invoice_origin'] = self.name

        result['context']['default_task_id'] = self.id
        result['context']['default_analytic_account_id'] = self.project_id.analytic_account_id.id


        result['domain'] = "[('task_id', '=', " + \
            str(self.id) + "), ('move_type', '=', 'in_invoice')]"

        return result

    def material_req_create(self):
        action = self.env.ref('construction_management_app.material_req_action')
        result = action.read()[0]


        # result['context']['default_task_id'] = self._origin.id

        result['domain'] = "[('task_id', '=', " + \
            str(self.id) + ")]"

        return result

    @api.depends('planning_ids', 'planning_ids.consumed')
    def _compute_total_consumed(self):
        for r in self:
            total_consumed = 0
            r.total_consumed = 0
            for plan in r.planning_ids:
                total_consumed+=plan.consumed

            r.total_consumed = total_consumed

    @api.depends('planning_ids', 'planning_ids.price_subtotal')
    def _compute_total_planned(self):
        for r in self:
            total_planned = 0
            r.total_planned = 0
            for plan in r.planning_ids:
                total_planned+=plan.price_subtotal

            r.total_planned = total_planned

    def unlink(self):
        for r in self:
            if r.project_id:
                if r.project_id.user_id.id != self.env.user.id:
                    raise UserError("Only the Project Manager can delete tasks.")
        return super(ProjectTask, self).unlink()

    # @api.multi
    def view_stock_moves(self):
        for rec in self:
            stock_move_list = []
            for move in rec.move_ids:
                stock_move_list.append(move.id)
        result = self.env.ref('stock.stock_move_action')
        action_ref = result or False
        result = action_ref.read()[0]
        result['domain'] = str([('id', 'in', stock_move_list)])
        return result

    # @api.multi
    def view_notes(self):
        for rec in self:
            res = self.env.ref('construction_management_app.action_task_note_note')
            res = res.read()[0]
            res['domain'] = str([('task_id','in',rec.ids)])
        return res
