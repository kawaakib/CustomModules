# -*- coding: utf-8 -*-

from odoo import models, fields, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # @api.multi
    @api.onchange('task_id',
                  'project_id',
                  'analytic_account_id')
    def onchange_project_task(self):
        for rec in self:
            rec.project_id = rec.task_id.project_id.id
            rec.analytic_account_id = rec.task_id.project_id.analytic_account_id.id

    # @api.multi
    @api.depends('move_lines',
                 'move_lines.product_id',
                 'product_id.boq_type')
    def compute_equipment_machine(self):
        eqp_machine_total = 0.0
        work_resource_total = 0.0
        work_cost_package_total = 0.0
        subcontract_total = 0.0
        for rec in self:
            for line in rec.move_lines:
                if line.product_id.boq_type == 'eqp_machine':
                    eqp_machine_total += line.product_id.standard_price * line.product_uom_qty
                if line.product_id.boq_type == 'worker_resource':
                    work_resource_total += line.product_id.standard_price * line.product_uom_qty
                if line.product_id.boq_type == 'work_cost_package':
                    work_cost_package_total += line.product_id.standard_price * line.product_uom_qty
                if line.product_id.boq_type == 'subcontract':
                    subcontract_total += line.product_id.standard_price * line.product_uom_qty
            rec.equipment_machine_total = eqp_machine_total
            rec.worker_resource_total = work_resource_total
            rec.work_cost_package_total = work_cost_package_total
            rec.subcontract_total = subcontract_total

    # @api.multi
    @api.depends('purchase_order_ids')
    def _purchase_order_count(self):
        for rec in self:
            rec.purchase_order_count = len(rec.purchase_order_ids)

    task_id = fields.Many2one(
        'project.task',
        string='Task / Job Order',
    )
    task_user_id = fields.Many2one(
        'res.users',
        related='task_id.user_id',
        string='Task / Job Order User'
    )

    material_reqisition_id = fields.Many2one('construction_management_app.material_req', string='Material Requistion')

    project_id = fields.Many2one(
        'project.project',
        string='Construction Project',
    )
    purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order',
    )
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
    )
    purchase_order_ids = fields.Many2many(
        'purchase.order',
        string='Purchase Orders',
    )
    purchase_order_count = fields.Integer(
        compute='_purchase_order_count',
        string="Purchase Orders",
        store=True,
    )
    equipment_machine_total = fields.Float(
        compute='compute_equipment_machine',
        string='Equipment / Machinery Cost',
        store=True,
    )
    worker_resource_total = fields.Float(
        compute='compute_equipment_machine',
        string='Worker / Resource Cost',
        store=True,
    )
    work_cost_package_total = fields.Float(
        compute='compute_equipment_machine',
        string='Work Cost Package',
        store=True,
    )
    subcontract_total = fields.Float(
        compute='compute_equipment_machine',
        string='Subcontract Cost',
        store=True,
    )
    is_boq_picking = fields.Boolean(
        string="BOQ Requisition?",
        copy=False
    )


    # @api.multi
    def view_purchase_order(self):
        # for rec in self:
        self.ensure_one()
        res = self.env.ref('construction_management_app.purchase_rfq_construction')
        res = res.read()[0]
        res['domain'] = str([('id','in',self.purchase_order_ids.ids)])
        return res

class StockMove(models.Model):
    _inherit = 'stock.move'
    _description = 'Stock Move Analytic'

    analytic_account_id = fields.Many2one(
        string="Analytic Account", comodel_name="account.analytic.account",
    )

    def _prepare_account_move_line(
        self, qty, cost, credit_account_id, debit_account_id, description
    ):
        self.ensure_one()
        res = super(StockMove, self)._prepare_account_move_line(
            qty, cost, credit_account_id, debit_account_id, description
        )
        # Add analytic account in debit line
        if not self.picking_id.analytic_account_id or not res:
            return res

        for num in range(0, 2):
            if (
                res[num][2]["account_id"]
                != self.product_id.categ_id.property_stock_valuation_account_id.id
            ):
                res[num][2].update({"analytic_account_id": self.picking_id.analytic_account_id.id})
        return res

    @api.model
    def _prepare_merge_moves_distinct_fields(self):
        fields = super()._prepare_merge_moves_distinct_fields()
        fields.append("analytic_account_id")
        return fields

class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    analytic_account_id = fields.Many2one(related="move_id.analytic_account_id")
