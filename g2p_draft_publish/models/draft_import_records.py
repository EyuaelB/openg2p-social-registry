from odoo import models, fields, api
import json
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime
import logging
from typing import Dict, List
_logger = logging.getLogger(__name__)


class BaseInherit(models.AbstractModel):
    _inherit = 'base'

    def web_save(self, vals, specification: Dict[str, Dict], next_id=None) -> List[Dict]:
        if self._name == 'res.partner' and  self.env.context.get('in_enrichment'):
            self.action_save_to_draft(vals)
            return self
        
        
        if self:
            self.write(vals)
        else:
            self = self.create(vals)
        if next_id:
            self = self.browse(next_id)
        return self.with_context(bin_size=True).web_read(specification)


class G2PDraftImportedRecord(models.Model):
    _name = "draft.imported.record"
    _description = "Draft Imported Records"
    _inherit = ['mail.thread', 'mail.activity.mixin'] 
    
    name = fields.Char(string='Name')
    given_name = fields.Char(string="First Name")
    family_name = fields.Char(string="Father's Name")
    addl_name = fields.Char(string="Grand Father's Name")
    phone = fields.Char(string="Phone")
    gender = fields.Char()
    region = fields.Char(string="Region")
   
    partner_data = fields.Json(string='Partner Data (JSON)')
    validation_status = fields.Many2one('g2p.validation.status')
    state = fields.Selection(string='State', selection=[('in_enrichment', 'Enrichment'), ('submitted', 'Submitted'), ('published', 'Published')], default="in_enrichment")
    import_record_id = fields.Many2one('g2p.imported.record',string='Import Record')
    rejection_reason = fields.Text()
    
    
    def action_publish(self):
        self.ensure_one()
        partner_data = json.loads(self.partner_data)
        res_partner_model = self.env['res.partner']

        # Fetch all fields metadata from res.partner
        fields_metadata = res_partner_model.fields_get()

        # Dictionary to store valid fields and values
        valid_data = {}
        
        given_name = partner_data.get('given_name', '')
        family_name = partner_data.get('family_name', '')
        gf_name_en = partner_data.get('addl_name', '')

        for field_name, value in partner_data.items():
            if field_name in fields_metadata:
                field_info = fields_metadata[field_name]
                field_type = field_info.get('type')

                # Validation based on field type
                if field_type == 'char' and isinstance(value, str):
                    valid_data[field_name] = value
                elif field_type == 'integer' and isinstance(value, int):
                    valid_data[field_name] = value
                elif field_type == 'float' and isinstance(value, (int, float)):
                    valid_data[field_name] = float(value)
                elif field_type == 'boolean' and isinstance(value, bool):
                    valid_data[field_name] = value
                elif field_type == 'many2one' and isinstance(value, int):
                    # Check if the referenced record exists
                    if self.env[field_info['relation']].browse(value).exists():
                        valid_data[field_name] = value
                elif field_type == 'selection':
                    selection_options = [option[0] for option in field_info.get('selection', [])]
                    if value in selection_options:
                        valid_data[field_name] = value

        # Create the res.partner record with valid data
        if valid_data:
            valid_data['db_import'] = 'yes'
            valid_data['name'] = f"{given_name} {family_name} {gf_name_en}".upper()
            
            new_partner = res_partner_model.create(valid_data)
            self.write({'state':'published'})
        else:
            raise ValueError("No valid data found to create a partner record.")
  

    def action_submit(self):
        self.write({'state':'submitted'})
    
    
    def action_open_wizard(self):
        
        self.ensure_one()
        active_id = self.id
        
        if not self.partner_data:
            raise UserError("No partner data available to edit.")
        try:
            json_data = json.loads(self.partner_data)
            
        except json.JSONDecodeError:
            raise UserError("Invalid JSON data in partner_data.")
        
        partner_model_fields = self.env['res.partner']._fields
        _logger.info("the set of fields")
        _logger.info(self.env['res.partner']._fields)
        _logger.info("the set of the json")
        _logger.info(json_data.items())
        additional_g2p_info = {}  
        context_data = {} 
         
        # excluded = ["land_information_ids", "crop_information_ids", "livestock_information_ids", "phone_number_ids", "reg_ids"]
       
        for field_name, field_value in json_data.items():
            
            if field_name not in partner_model_fields:  
                additional_g2p_info[field_name] = field_value
                continue
     

            field = partner_model_fields[field_name]
            
            if field.type == 'datetime' and isinstance(field_value, str):
                _logger.info(f"the datetime field {field_name}")
                try:
                    field_value = datetime.fromisoformat(field_value)
                    context_data[f"default_{field_name}"] = field_value
                except ValueError:
                    pass  
                
            elif field.type == 'date' and isinstance(field_value, str):
                try:
                    field_value = date.fromisoformat(field_value)
                    context_data[f"default_{field_name}"] = field_value
                except ValueError:
                    pass  # If it's not a valid date string, leave it as is
                
            elif field.type == 'many2one':
                # _logger.info(f"the many2one field 01 {field_name}")
                try:
                    field_value = int(field_value)
                    if isinstance(field_value, int):
                        context_data[f"default_{field_name}"] = json_data[field_name]
                        _logger.info(f"the many2one field {field_name}")
                except ValueError as e:
                    if not isinstance(field_value, int): 
                        additional_g2p_info[field_name] = field_value
             
            elif field.type == 'many2many':
                # _logger.info(f"the field {field_name}")
                if isinstance(field_value, list):
                    if all(isinstance(val, int) for val in field_value):
                        # If field_value is a list of IDs (int), update the many2many field
                        context_data[f"default_{field_name}"] = [(6, 0, field_value)]
                    elif all(hasattr(val, 'id') for val in field_value):
                        # If field_value is a list of records, extract their IDs
                        context_data[f"default_{field_name}"] = [(6, 0, [val.id for val in field_value])]
                    else:
                        additional_g2p_info[field_name] = field_value
                elif hasattr(field_value, 'id'):  # If field_value is a single record
                    # If field_value is a single record, update it as a list with one record
                    context_data[f"default_{field_name}"] = [(6, 0, [field_value.id])]
                else:
                    additional_g2p_info[field_name] = field_value
              
 
            elif field.type == 'selection':
                _logger.info(f"the field {field_name}")
                selection_values = field.get_values(env=self.env)
                if field_value in selection_values:
                    context_data[f"default_{field_name}"] = field_value
                if field_value not in selection_values:
                    additional_g2p_info[field_name] = field_value
           
            else:
                context_data[f"default_{field_name}"] = field_value
                
        context_data['active_id'] = active_id 
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Record Data',
            'view_mode': 'form',
            'res_model': 'res.partner',
            'view_id': self.env.ref('g2p_draft_publish.g2p_validation_form_view').id,
            'target': 'new',
            # 'target': 'current',
            'context': {**context_data,  'default_additional_g2p_info': json.dumps(additional_g2p_info),
                        'in_enrichment' : 'yes',
                        'default_phone_number_ids': json_data.get('phone_number_ids', []),
                        'default_individual_membership_ids': json_data.get('individual_membership_ids', []),
                        'default_reg_ids': json_data.get('reg_ids', [])
                        },
        }
    
    
  
    def action_reject(self):
         return {
                'name': 'Confirm Rejection',
                'type': 'ir.actions.act_window',
                'res_model': 'reject.wizard',
                'view_mode': 'form',
                'target': 'new',
                }   


class G2PRespartnerIntegration(models.Model):
    _inherit = 'res.partner'
    
    db_import = fields.Selection(string="Imported", index=True, selection=[("yes", "Yes"), ("no", "No")],default="no")

    def action_update(self):
        return
    
    
    def action_save_to_draft(self,vals):
        
        context = self.env.context
        model_name = context.get('active_model')
        record_id = context.get('active_id')
        active_record = self.env[model_name].browse(record_id)
        partner_data = json.loads(active_record.partner_data) or {}
        
        
        m2m_fields = {
                    'tags_ids': 'tags_ids',
                    }

        processed_m2m_fields = {}
        for field, key in m2m_fields.items():
            processed_m2m_fields[field] = [item[1] for item in vals.get(field, [])]


        dynamic_fields = {
            'is_company': False,
            'is_group': False,
            'is_registrant': True,
            'db_import': 'yes',
            **processed_m2m_fields
         
        }

        static_fields = [
            'given_name', 'family_name', 'address', 'addl_name', 'birthdate','region',
             'email', 'gender', 'civil_status', 'district','occupation', 'birthdate_not_exact', 'income','brith_place'
      'martial_status', 'education',
            'is_disabled', 'phone_number_ids','related_1_ids', 'related_2_ids', 'individual_membership_ids','group_memebership_ids', 'reg_ids', 
            'additional_g2p_info'
        ]


        draft_record = {}

        draft_record.update(dynamic_fields)

        for field in static_fields:
            if field in self.env[model_name]._fields:
                draft_record[field] = vals.get(field) or partner_data.get(field)
            else:
                if vals.get(field):
                    draft_record[field] = vals[field]

        if vals.get('given_name') or vals.get('family_name') or vals.get('addl_name'):
            draft_record['name'] = f"{vals.get('given_name', '').upper()} {vals.get('family_name', '').upper()} {vals.get('addl_name', '').upper()}".strip()

        
        active_record.write({
            'partner_data': json.dumps(draft_record)
        })


    

    def action_publish(self):
        context = self.env.context
        model_name = context.get('active_model')
        record_id = context.get('active_id')
        record = self.env[model_name].browse(record_id)
        if record.state=='published':
            raise ValidationError("Record already has been published")
        else:
            record.action_publish()
    
    
    def action_submit(self):
        context = self.env.context
        model_name = context.get('active_model')
        record_id = context.get('active_id')
        record = self.env[model_name].browse(record_id)
        if record.state=='submitted':
            raise ValidationError("Record already has been Submitted")
        else:
            record.action_submit()
    
    
    
