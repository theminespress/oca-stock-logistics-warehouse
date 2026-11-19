- With **Apply unit rounding everywhere** off, a few places in Odoo still read a
  unit's `rounding` field directly instead of calling `uom.uom.compare()` /
  `is_zero()`; they keep using the *Product Unit* precision, as intended.
- Odoo 20 removes the `rounding` field from `uom.uom` and converts quantities with the
  *Product Unit* precision directly: the 20.0 version has to restore the field and
  override `_compute_quantity()` as well.
