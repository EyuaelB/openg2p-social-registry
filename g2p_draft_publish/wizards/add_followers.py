from odoo import _, models
from odoo.exceptions import UserError
from odoo.tools import is_html_empty

# class MailFollowers(models.Model):
#     _inherit = 'mail.followers'

#     assignee_id = fields.Many2one('res.users', string='Assignee')


class Invite(models.TransientModel):
    _inherit = "mail.wizard.invite"

    def add_followers_for_multiple_records(self):
        if not self.env.user.email:
            raise UserError(_("Unable to post message, please configure the sender's email address."))

        email_from = self.env.user.email_formatted

        # Ensure active_model and active_ids are present in the context
        if not self._context.get("active_model") or not self._context.get("active_ids"):
            raise UserError(_("No active model or records specified in the context."))

        active_model = self._context["active_model"]
        active_ids = self._context["active_ids"]

        # for record_id in active_ids:
        #     record = self.env[active_model].browse(record_id)
        #     record.assigned_to = self.env.user

        Model = self.env[active_model]
        documents = Model.browse(active_ids)

        for wizard in self:
            new_partners = wizard.partner_ids - documents.sudo().mapped("message_partner_ids")

            # Add the partners as followers
            documents.message_subscribe(partner_ids=new_partners.ids)

            model_name = self.env["ir.model"]._get(active_model).display_name

            # Send a notification if the option is checked and if a message exists
            if wizard.notify and wizard.message and not is_html_empty(wizard.message):
                for document in documents:
                    message_values = wizard._prepare_message_values(document, model_name, email_from)
                    message_values["partner_ids"] = new_partners.ids
                    document.message_notify(**message_values)

        return {"type": "ir.actions.act_window_close"}
