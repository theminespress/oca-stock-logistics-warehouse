# Copyright 2026 Cybernexus Solutions
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
{
    "name": "Units of Measure Rounding",
    "summary": "Give a unit of measure its own rounding precision, such as whole "
    "units only, as before Odoo 19",
    "version": "19.0.1.0.0",
    "author": "Cybernexus Solutions, Odoo Community Association (OCA)",
    "development_status": "Beta",
    "website": "https://github.com/OCA/stock-logistics-warehouse",
    "category": "Inventory/Inventory",
    "depends": ["stock"],
    "data": [
        "views/uom_uom_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
}
