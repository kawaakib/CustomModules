from odoo import models, fields, api
from datetime import datetime

class MaterialRequisition(models.Model):
    _name = "construction_management_app.material_req"
    _description = "Material Requisition"

    name = fields.Char(string='Number', readonly=True, copy=False, default='New')

    task_user_id = fields.Many2one('res.users', related='task_id.user_id', string='Task / Job Order User')

    task_id = fields.Many2one('project.task', string='Task / Job Order')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env['res.company']._company_default_get())

    currency_id = fields.Many2one('res.currency', 'Currency', required=True, \
                                  default=lambda self: self.env.user.company_id.currency_id.id)
    project_id = fields.Many2one(
        'project.project',
        string='Construction Project',
    )

    type = fields.Selection([
        ('plan', 'Plan'),
        ('requistion', 'Requistion')], 'Type')

    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
    )

    bill_ids = fields.One2many(
        'account.move',
        'material_reqisition_id',
        string='Bills',
        domain=[('move_type','=', 'in_invoice')]
    )

    picking_ids = fields.One2many(
        'stock.picking',
        'material_reqisition_id',
        string='Pickings',
    )
    bill_count = fields.Integer(
        compute='_bill_count',
        string="Bills",
        store=True,
    )

    picking_count = fields.Integer(
        compute='_picking_count',
        string="Delivery Order",
        store=True,
    )

    material_req_line_ids = fields.One2many('construction_management_app.material_req_line', 'material_reqisition_id')

    def action_create_bill(self):
        invoice = self.env['account.move']
        invoice_line = self.env['account.move.line']

        for r in self:
            journal_domain = [('type', '=', 'purchase'),('company_id', '=', self.env.company.id)]
            default_journal_id = self.env['account.journal'].search(journal_domain, order="id asc", limit=1)

            inserted_invoice = invoice.create({
                # 'name': origin,
                'journal_id':default_journal_id.id, #journal_id,
                'company_id': r.company_id.id,
                'currency_id': r.currency_id.id,
                'move_type': 'in_invoice',
                'invoice_origin': r.name,
                'narration': r.task_id.name,
                'material_reqisition_id': r.id,
                'project_id': r.project_id.id,
            })

            if r.material_req_line_ids:
                for line in r.material_req_line_ids:
                    inserted_invoice.write({
                        'invoice_line_ids': [(0,0, {
                            'product_id': line.product_id.id,
                            'name':line.product_id.name,
                            'quantity': line.quantity,
                            'product_uom_id': line.product_uom.id,
                            'price_unit': line.rate,
                            'account_id': (line.product_id.property_account_expense_id or line.product_id.categ_id.property_account_expense_categ_id).id,
                            'move_id': inserted_invoice.id,
                            'company_id': self.env.company.id
                        })]

                    })

            # self.write({
            #     'bill_ids': self.env['account.move'].search([('id', 'in', [inserted_invoice.id])]).ids
            # })

            action = self.env.ref('account.action_move_in_invoice_type').read()[0]
            action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
            action['res_id'] = inserted_invoice.id
            # inserted_invoice.project_id = 2
            return action

    @api.onchange('project_id')
    def _onchange_project_id(self):
        res = {}
        for r in self:
            if r.project_id:
                # task domain
                res['domain'] = {'task_id': [('project_id', '=', r.project_id.id)]}

                #get analytic_account_id from parent project_id
                if r.project_id.is_a_sup_project:
                    project_obj = self.env['project.project']
                    parent_proj = project_obj.search([('subtask_project_id', '=', r.project_id.id)], limit=1)
                    r.analytic_account_id = parent_proj.analytic_account_id.id if parent_proj.analytic_account_id else False
                elif not r.project_id.is_a_sup_project:
                    r.analytic_account_id = r.project_id.analytic_account_id.id if r.project_id.analytic_account_id else False
        return res

    @api.onchange('task_id')
    def _onchange_task_id(self):
        for r in self:
            r.material_req_line_ids = False
            if r.task_id.planning_ids:
                for line in r.task_id.planning_ids:
                    r.material_req_line_ids = [(0,0, {
                        'product_id':line.product_id.id,
                        'name': line.name,
                        'quantity':line.quantity,
                        'rate':line.rate,
                        'plan_id': line._origin.id
                    })]

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for r in self:
            if r.product_id:
                r.rate = r.product_id.lst_price
                r.name = r.product_id.name
        # res = {}
        # for r in self:
        #     if r.task_id:
        #         res['domain'] = {'project_id': [('id', '=', r.task_id.project_id.id)]}
        # return res
    @api.depends('bill_ids')
    def _bill_count(self):
        for rec in self:
            rec.bill_count = len(rec.bill_ids)

    @api.depends('picking_ids')
    def _picking_count(self):
        for rec in self:
            rec.picking_count = len(rec.picking_ids)

    def view_vendor_bill(self):
        # for rec in self:
        self.ensure_one()
        res = self.env.ref('account.action_move_in_invoice_type')
        res = res.read()[0]
        res['context'] = {'default_move_type': 'in_invoice', 'default_analytic_account_id': self.analytic_account_id.id}
        res['domain'] = str([('id','in',self.bill_ids.ids)])
        return res

    def view_delivery_order(self):
        # for rec in self:
        self.ensure_one()
        res = self.env.ref('stock.stock_picking_action_picking_type')
        res = res.read()[0]
        res['domain'] = str([('id','in',self.picking_ids.ids)])
        return res

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('construction_management_app.material_req')
        result = super(MaterialRequisition, self).create(vals)

        return result

class MaterialRequisitionLine(models.Model):
    _name = "construction_management_app.material_req_line"
    _description = "Material Requisition Line"

    material_reqisition_id = fields.Many2one('construction_management_app.material_req', string='Material Requistion')
    product_id = fields.Many2one('product.product', string="Product")
    name = fields.Char(string="Description")
    quantity = fields.Float('Quantity', default=1)
    material_req_type = fields.Char('Type')
    product_uom = fields.Many2one(
        'uom.uom',
        'Unit of Measure'
    )
    rate = fields.Float('Unit Price')
    price_subtotal = fields.Monetary(string="Total", compute="_compute_price_subtotal")
    currency_id = fields.Many2one('res.currency', 'Currency', required=True, \
                                  default=lambda self: self.env.user.company_id.currency_id.id)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env['res.company']._company_default_get())
    task_id = fields.Many2one('project.task', string='Task / Job Order')
    plan_id = fields.Many2one('construction_management_app.material_conceptions', string='Plan')



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
    # @api.model
    # def create(self, vals):
    #     result = super(MaterialRequisitionLine, self).create(vals)
    #     result._onchange_product_id()
    #     # result._onchange_material_reqisition_id_id()
    #     return result

class MaterialConceptions(models.Model):
    _name = "construction_management_app.material_conceptions"
    _description = "Material Conceptions"

    material_req_line_ids = fields.One2many('construction_management_app.material_req_line', 'plan_id', string='Material Requistion')
    product_id = fields.Many2one('product.product', string="Product")
    name = fields.Char(string="Description")
    quantity = fields.Float('Quantity', default=1)
    product_uom = fields.Many2one(
        'uom.uom',
        'Unit of Measure'
    )
    rate = fields.Float('Unit Price')
    price_subtotal = fields.Monetary(string="Total", compute="_compute_price_subtotal")
    consumed_qty = fields.Float(string="Qty Consumed", compute="_compute_qty_consumed")
    consumed_uprice = fields.Float(string="Consumed U.Price", compute="_compute_rate_consumed")
    consumed = fields.Monetary(string="Total Consumed", compute="_compute_consumed")
    currency_id = fields.Many2one('res.currency', 'Currency', required=True, \
                                  default=lambda self: self.env.user.company_id.currency_id.id)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env['res.company']._company_default_get())
    task_id = fields.Many2one('project.task', string='Task / Job Order')




    @api.onchange('product_id')
    def _onchange_product_id(self):
        for r in self:
            if r.product_id:
                r.rate = r.product_id.lst_price
                r.name = r.product_id.name

    @api.depends('material_req_line_ids', 'material_req_line_ids.quantity', 'material_req_line_ids.rate')
    def _compute_qty_consumed(self):
        for r in self:
            consumed_qty = 0
            r.consumed_qty = 0
            # if r.material_req_line_ids.filtered(lambda r: r.product_id == r.product_id.id):
            for line in r.material_req_line_ids:
                if line.product_id.id == r.product_id.id:
                    consumed_qty += line.quantity

            r.consumed_qty = consumed_qty

    @api.depends('material_req_line_ids', 'material_req_line_ids.quantity', 'material_req_line_ids.rate')
    def _compute_rate_consumed(self):
        for r in self:
            for r in self:
                r.consumed_uprice = 0
                if r.consumed_qty or r.consumed:
                    r.consumed_uprice = r.consumed / r.consumed_qty

    @api.depends('material_req_line_ids', 'material_req_line_ids.quantity', 'material_req_line_ids.rate')
    def _compute_consumed(self):
        for r in self:
            # consumed_qty = 0
            # consumed_uprice = 0
            consumed = 0
            r.consumed = 0
            # if r.material_req_line_ids.filtered(lambda r: r.product_id == r.product_id.id):
            for line in r.material_req_line_ids:
                if line.product_id.id == r.product_id.id:
                    # consumed_qty += line.quantity
                    # consumed_uprice += line.rate
                    consumed += line.price_subtotal

            # r.consumed_qty = consumed_qty
            # r.consumed_uprice = consumed_uprice
            r.consumed = consumed
