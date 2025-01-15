from odoo import fields, models


class G2PValidationStatus(models.Model):
    _name = "g2p.validation.status"

    name = fields.Char()
