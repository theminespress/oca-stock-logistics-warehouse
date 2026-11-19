# Copyright 2026 Cybernexus Solutions
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare, float_is_zero, float_round, str2bool

EVERYWHERE_PARAM = "uom_rounding.everywhere"


class UomUom(models.Model):
    _inherit = "uom.uom"

    rounding_precision = fields.Float(
        digits=0,
        help="Quantities in this unit are rounded to a multiple of this value, "
        "e.g. 1 to always use whole units. Leave empty to use the 'Product Unit' "
        "decimal precision, like every unit in standard Odoo.",
    )
    # Core labels this computed field "Rounding Precision"; free that label for the
    # value people set, and say what this one is.
    rounding = fields.Float(string="Effective Rounding")

    _rounding_precision_not_negative = models.Constraint(
        "CHECK (rounding_precision >= 0)",
        "The rounding precision of a unit of measure cannot be negative.",
    )

    @api.model
    def _uom_rounding_everywhere(self):
        """Whether the unit's rounding precision applies everywhere (comparisons,
        conversions, `rounding`), as in Odoo 18, or only to `round()`."""
        param = self.env["ir.config_parameter"].sudo().get_param(EVERYWHERE_PARAM)
        return str2bool(param or "False", False)

    @api.depends("rounding_precision")
    def _compute_rounding(self):
        super()._compute_rounding()
        if not self._uom_rounding_everywhere():
            return
        for uom in self:
            if uom.rounding_precision:
                uom.rounding = uom.rounding_precision

    @api.constrains("rounding_precision")
    def _check_rounding_precision(self):
        digits = self.env["decimal.precision"].precision_get("Product Unit")
        smallest = 10**-digits
        for uom in self:
            if uom.rounding_precision < 0:
                raise ValidationError(
                    self.env._(
                        "The rounding precision of %(uom)s cannot be negative.",
                        uom=uom.display_name,
                    )
                )
            # Quantities are stored with `digits` decimals: a precision that isn't a
            # multiple of 10**-digits (finer, or e.g. 0.15 with 1 digit) would give
            # quantities that can't be stored, and that validation would refuse.
            if uom.rounding_precision and (
                float_compare(
                    float_round(uom.rounding_precision, precision_digits=digits),
                    uom.rounding_precision,
                    precision_digits=digits + 4,
                )
                != 0
            ):
                raise ValidationError(
                    self.env._(
                        "The rounding precision of %(uom)s must be a multiple of "
                        "%(smallest)s, the 'Product Unit' decimal precision: "
                        "quantities are not stored with more decimals than that.",
                        uom=uom.display_name,
                        smallest=f"{smallest:.{digits}f}",
                    )
                )

    def round(self, value, rounding_method="HALF-UP"):
        self.ensure_one()
        if self.rounding_precision:
            return float_round(
                value,
                precision_rounding=self.rounding_precision,
                rounding_method=rounding_method,
            )
        return super().round(value, rounding_method=rounding_method)

    def compare(self, value1, value2):
        self.ensure_one()
        if self.rounding_precision and self._uom_rounding_everywhere():
            return float_compare(
                value1, value2, precision_rounding=self.rounding_precision
            )
        return super().compare(value1, value2)

    def is_zero(self, value):
        self.ensure_one()
        if self.rounding_precision and self._uom_rounding_everywhere():
            return float_is_zero(value, precision_rounding=self.rounding_precision)
        return super().is_zero(value)
