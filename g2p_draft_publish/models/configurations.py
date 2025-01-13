from odoo import models, fields, api, _


class G2PValidationStatus(models.Model):
    _name = 'g2p.validation.status'
    
    name = fields.Char()
    
    
