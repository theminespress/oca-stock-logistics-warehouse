# Copyright 2026 Cybernexus Solutions
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import fields, models

from .uom_uom import EVERYWHERE_PARAM


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    uom_rounding_everywhere = fields.Boolean(
        string="Apply unit rounding everywhere",
        config_parameter=EVERYWHERE_PARAM,
        help="Off: a unit's rounding precision is used when Odoo rounds a quantity "
        "(e.g. components to consume). On: it is also used to convert and compare "
        "quantities, as in Odoo 18 and earlier.",
    )
