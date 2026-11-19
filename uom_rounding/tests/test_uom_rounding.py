# Copyright 2026 Cybernexus Solutions
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo.exceptions import UserError, ValidationError
from odoo.tests import Form, TransactionCase, tagged

from odoo.addons.uom_rounding.models.uom_uom import EVERYWHERE_PARAM


@tagged("post_install", "-at_install")
class TestUomRounding(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.unit = cls.env.ref("uom.product_uom_unit")
        cls.digits = cls.env["decimal.precision"].precision_get("Product Unit")
        cls.global_rounding = 10**-cls.digits
        # A unit consumed whole: one sheet of paper.
        cls.sheet = cls.env["uom.uom"].create(
            {
                "name": "Test Sheet",
                "relative_factor": 1.0,
                "relative_uom_id": cls.unit.id,
                "rounding_precision": 1.0,
            }
        )
        # A unit left as in standard Odoo.
        cls.roll = cls.env["uom.uom"].create(
            {
                "name": "Test Roll",
                "relative_factor": 1.0,
                "relative_uom_id": cls.unit.id,
            }
        )
        cls.box_of_10 = cls.env["uom.uom"].create(
            {
                "name": "Test Box of 10",
                "relative_factor": 10.0,
                "relative_uom_id": cls.unit.id,
            }
        )

    def _sheet_stock(self, quantity):
        """A product counted in sheets, with `quantity` on hand, stocked while the
        unit had no precision of its own."""
        precision = self.sheet.rounding_precision
        self.sheet.rounding_precision = 0.0
        paper = self.env["product.product"].create(
            {"name": "Test Paper", "is_storable": True, "uom_id": self.sheet.id}
        )
        location = (
            self.env["stock.warehouse"]
            .search([("company_id", "=", self.env.company.id)], limit=1)
            .lot_stock_id
        )
        self.env["stock.quant"]._update_available_quantity(paper, location, quantity)
        self.sheet.rounding_precision = precision
        quant = self.env["stock.quant"]._gather(paper, location)
        return paper, quant

    def _set_everywhere(self, value):
        self.env["ir.config_parameter"].sudo().set_param(EVERYWHERE_PARAM, value)
        self.env.invalidate_all()

    def test_unset_unit_behaves_like_standard(self):
        self.assertEqual(self.roll.rounding, self.global_rounding)
        self.assertEqual(self.roll.round(20.4, rounding_method="UP"), 20.4)
        self._set_everywhere(True)
        self.assertEqual(self.roll.rounding, self.global_rounding)
        self.assertEqual(self.roll.compare(20.4, 20.0), 1)
        self.assertFalse(self.roll.is_zero(0.4))

    def test_round_uses_unit_precision(self):
        self.assertEqual(self.sheet.round(20.4, rounding_method="UP"), 21.0)
        self.assertEqual(self.sheet.round(20.4), 20.0)
        self.assertEqual(self.sheet.round(20.5), 21.0)
        self.assertEqual(self.sheet.round(20.4, rounding_method="DOWN"), 20.0)

    def test_on_hand_rounded_to_unit(self):
        # Like Odoo 18: quantities Odoo rounds, on-hand included, use the unit's
        # precision, even with the setting off.
        paper, _quant = self._sheet_stock(20.4)
        self.assertEqual(paper.qty_available, 20.0)
        self.sheet.rounding_precision = 0.0
        self.env.invalidate_all()
        self.assertAlmostEqual(paper.qty_available, 20.4)

    def test_fractional_done_quantity_refused(self):
        # Like Odoo 18: a done quantity that isn't a multiple of the unit's precision
        # can't be validated, so leftover fractional stock can't be adjusted either.
        _paper, quant = self._sheet_stock(20.4)
        quant.inventory_quantity = 20.0
        with self.assertRaisesRegex(UserError, "rounding precision"):
            quant.action_apply_inventory()

    def test_fractional_stock_cleanup(self):
        # The documented way out: clear the unit's precision, adjust, set it again.
        paper, quant = self._sheet_stock(20.4)
        self.sheet.rounding_precision = 0.0
        quant.inventory_quantity = 21.0
        quant.action_apply_inventory()
        self.sheet.rounding_precision = 1.0
        self.env.invalidate_all()
        self.assertEqual(paper.qty_available, 21.0)
        self.assertEqual(quant.quantity, 21.0)

    def test_setting_off_keeps_comparisons_and_conversions_global(self):
        self._set_everywhere(False)
        self.assertEqual(self.sheet.rounding, self.global_rounding)
        self.assertEqual(self.sheet.compare(20.4, 20.0), 1)
        self.assertFalse(self.sheet.is_zero(0.4))
        # 0.25 box of 10 = 2.5 units: not rounded to a whole sheet on conversion.
        self.assertEqual(self.box_of_10._compute_quantity(0.25, self.sheet), 2.5)

    def test_setting_on_applies_everywhere(self):
        self._set_everywhere(True)
        self.assertEqual(self.sheet.rounding, 1.0)
        self.assertEqual(self.sheet.compare(20.4, 20.0), 0)
        self.assertEqual(self.sheet.compare(20.6, 20.0), 1)
        self.assertTrue(self.sheet.is_zero(0.4))
        # Conversions round up to the unit's precision by default, as in Odoo 18.
        self.assertEqual(self.box_of_10._compute_quantity(0.25, self.sheet), 3.0)

    def test_settings_field(self):
        settings = self.env["res.config.settings"].create(
            {"uom_rounding_everywhere": True}
        )
        settings.execute()
        self.env.invalidate_all()
        self.assertTrue(self.env["uom.uom"]._uom_rounding_everywhere())
        self.assertEqual(self.sheet.rounding, 1.0)
        settings = self.env["res.config.settings"].create(
            {"uom_rounding_everywhere": False}
        )
        settings.execute()
        self.env.invalidate_all()
        self.assertFalse(self.env["uom.uom"]._uom_rounding_everywhere())

    def test_rounding_follows_changes(self):
        self._set_everywhere(True)
        self.assertEqual(self.sheet.rounding, 1.0)
        self.sheet.rounding_precision = 0.5
        self.assertEqual(self.sheet.rounding, 0.5)
        self.sheet.rounding_precision = 0.0
        self.assertEqual(self.sheet.rounding, self.global_rounding)

    def test_constraints(self):
        with self.assertRaises(ValidationError):
            self.roll.rounding_precision = self.global_rounding / 10
        with self.assertRaises(ValidationError):
            self.roll.rounding_precision = self.global_rounding * 1.5
        self.roll.rounding_precision = self.global_rounding
        self.roll.rounding_precision = 0.5

    def test_negative_precision_rejected(self):
        with self.assertRaises(ValidationError):
            self.roll.rounding_precision = -1.0

    def test_form(self):
        with Form(self.roll) as form:
            form.rounding_precision = 1.0
        self.assertEqual(self.roll.rounding_precision, 1.0)


@tagged("post_install", "-at_install")
class TestUomRoundingMrp(TransactionCase):
    """mrp is not a dependency: these run where it is installed."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if "mrp.production" not in cls.env:
            return
        unit = cls.env.ref("uom.product_uom_unit")
        cls.sheet = cls.env["uom.uom"].create(
            {
                "name": "Test Sheet",
                "relative_factor": 1.0,
                "relative_uom_id": unit.id,
                "rounding_precision": 1.0,
            }
        )
        cls.paper = cls.env["product.product"].create(
            {
                "name": "Test Paper",
                "is_storable": True,
                "uom_id": cls.sheet.id,
            }
        )
        cls.card = cls.env["product.product"].create(
            {"name": "Test Business Card", "is_storable": True, "uom_id": unit.id}
        )
        # 25 cards per sheet.
        cls.bom = cls.env["mrp.bom"].create(
            {
                "product_tmpl_id": cls.card.product_tmpl_id.id,
                "product_qty": 1.0,
                "bom_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.paper.id,
                            "product_qty": 0.04,
                            "product_uom_id": cls.sheet.id,
                        },
                    )
                ],
            }
        )

    def setUp(self):
        super().setUp()
        if "mrp.production" not in self.env:
            self.skipTest("mrp is not installed")

    def _create_mo(self, qty):
        return self.env["mrp.production"].create(
            {"product_id": self.card.id, "product_qty": qty, "bom_id": self.bom.id}
        )

    def test_components_rounded_up_to_whole_sheets(self):
        mo = self._create_mo(510)
        mo.action_confirm()
        self.assertEqual(mo.move_raw_ids.product_uom_qty, 21.0)

    def test_pick_components_whole_sheets(self):
        # A warehouse of its own, with the standard 2-step rules: an existing one may
        # be configured differently (e.g. make-to-stock components).
        warehouse = self.env["stock.warehouse"].create(
            {"name": "Test 2-step", "code": "TUR2", "manufacture_steps": "pbm"}
        )
        mo = self.env["mrp.production"].create(
            {
                "product_id": self.card.id,
                "product_qty": 510,
                "bom_id": self.bom.id,
                "picking_type_id": warehouse.manu_type_id.id,
            }
        )
        mo.action_confirm()
        self.assertEqual(mo.move_raw_ids.product_uom_qty, 21.0)
        if not mo.picking_ids:
            self.skipTest(
                "this database's 2-step rules don't create Pick Components "
                "transfers when a manufacturing order is confirmed"
            )
        pick_moves = mo.picking_ids.move_ids.filtered(
            lambda m: m.product_id == self.paper
        )
        self.assertEqual(sum(pick_moves.mapped("product_uom_qty")), 21.0)

    def test_changed_quantity_rounded_up(self):
        mo = self._create_mo(500)
        mo.action_confirm()
        self.assertEqual(mo.move_raw_ids.product_uom_qty, 20.0)
        self.env["change.production.qty"].create(
            {"mo_id": mo.id, "product_qty": 610}
        ).change_prod_qty()
        self.assertEqual(mo.move_raw_ids.product_uom_qty, 25.0)

    def test_unit_without_precision_stays_fractional(self):
        self.sheet.rounding_precision = 0.0
        mo = self._create_mo(510)
        mo.action_confirm()
        self.assertAlmostEqual(mo.move_raw_ids.product_uom_qty, 20.4)
