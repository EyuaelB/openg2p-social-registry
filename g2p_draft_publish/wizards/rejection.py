import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)



class RejectWizard(models.TransientModel):
    _name = 'reject.wizard'
    _description = 'Reject Wizard'

    rejection_reason = fields.Text(string="Reason for Rejection", required=True)

    def confirm_rejection(self):
        active_ids = self._context.get('active_ids')
        self.ensure_one()
        record = self.env['draft.imported.record'].browse(active_ids[0])
        
        record.write({
            'state': 'in_enrichment',
            'rejection_reason': self.rejection_reason,
        })
        
        record.message_post(
            body=f"Record rejected: {self.rejection_reason}"
            
        )
        
        
        validator_group = self.env.ref("g2p_ati_integrations.group_int_validator")
        validator_users = validator_group.users
        matching_users = validator_users.filtered(lambda user: user.partner_id.id in record.message_partner_ids.ids)
                
        
        
        
        if matching_users:
            for user in matching_users:
                self.env["mail.activity"].create(
                            {
                                "activity_type_id": self.env.ref(
                                    "mail.mail_activity_data_todo"
                                ).id,  
                                "res_model_id": self.env["ir.model"]
                                .search([("model", "=", "draft.imported.record")])
                                .id,
                                "res_id": record.id,  
                                "user_id": user.id,
                                # "date_deadline": fields.Date.context_today(self),  
                                "summary": "Record Rejected",
                                "note": f"Reason: {self.rejection_reason}. Please review and sumbit again.",
                            }
                        )
            
        return {'type': 'ir.actions.act_window_close'}
