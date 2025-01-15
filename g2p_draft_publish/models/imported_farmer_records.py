import json

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class G2PImportedRecord(models.Model):
    _name = "g2p.imported.record"
    _description = "Imported Record"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char()
    given_name = fields.Char(string="First Name")
    family_name = fields.Char(string="Father's Name")
    gf_name_eng = fields.Char(string="Grand Father's Name")
    phone = fields.Char()
    gender = fields.Char()
    region = fields.Char()
    state = fields.Selection(selection=[("draft", "Draft"), ("moved", "Created")], default="draft")
    language = fields.Char()
    record_from = fields.Char()
    record_type = fields.Selection(selection=[("single", "Single Source"), ("composed", "Composed")])
    db_import = fields.Boolean("Imported", default=False)

    @api.onchange("family_name", "given_name", "gf_name_eng")
    def name_change_farmer(self):
        name = ""
        if self.given_name:
            name += self.given_name + " "
        if self.family_name:
            name += self.family_name + " "
        if self.gf_name_eng:
            name += self.gf_name_eng

        self.name = name.upper()

    def action_view_draft_records(self):
        return {
            "name": "Draft Records",
            "type": "ir.actions.act_window",
            "res_model": "draft.imported.record",
            "view_mode": "kanban,form",
            "domain": [("import_record_id", "=", self.id)],
            "context": dict(self.env.context, default_import_record_id=self.id),
        }

    def action_to_draft(self):
        for record in self:
            associated_records = (
                self.env["draft.imported.record"].sudo().search([("import_record_id", "=", record.id)])
            )

            if any(rec.state == "published" for rec in associated_records):
                raise ValidationError(
                    _("Cannot set to draft. There are associated records that are already published.")
                )

            associated_records.unlink()
            record.write({"state": "draft"})

    def action_move(self):
        self.write({"state": "moved"})

    def create_draft_imported_record(self):
        self.ensure_one()

        enrichment_started = self.env.ref("g2p_draft_publish.enrichment_started")

        partner_data = {
            "given_name": self.given_name,
            "family_name": self.family_name,
            "addl_name": self.gf_name_eng,
            "phone": self.phone,
            "gender": self.gender,
            "region": self.region,
        }

        data = {
            "name": self.name,
            "given_name": self.given_name,
            "family_name": self.family_name,
            "addl_name": self.gf_name_eng,
            "phone": self.phone,
            "gender": self.gender,
            "region": self.region,
            "import_record_id": self.id,
            "partner_data": json.dumps(partner_data),
            "validation_status": enrichment_started.id,
        }

        new_record = self.env["draft.imported.record"].sudo().create(data)
        new_record.sudo().write({"message_partner_ids": [(6, 0, self.message_partner_ids.ids)]})

        self.write({"state": "moved"})

        return {
            "name": "Draft Records",
            "type": "ir.actions.act_window",
            "res_model": "draft.imported.record",
            "view_mode": "kanban,form,tree",
            "domain": [("import_record_id", "=", self.id)],
            "context": dict(self.env.context, default_import_record_id=self.id),
        }
