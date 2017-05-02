from . import Validator, ValidationError
from ..changes import Change


class MaxLengthValidator(Validator):
    accept_codes = [Change.UPDATE]
    code = 8
    msg = u'Too long {field_name}, the {field_name} exceeds {max_length} characters: {field_value}'

    def validate(self, result):
        fields_max_length = self.settings.get('fields_max_length', {})
        _, change_data = result.change_data()
        changes = change_data['changes']
        for field in changes:
            _, new_val = changes[field]
            max_length = fields_max_length.get(field)
            if max_length:
                max_length = int(max_length)
            if max_length and len(new_val) > max_length:
                yield ValidationError(self.code, self.msg.format(field_name=field, max_length=max_length,
                                                                 field_value=new_val))


class SKUChangeValidator(Validator):
    accept_codes = [Change.UPDATE]
    code = 9
    msg = u'The crawl contains sku changes for product {product}. old: {old_sku}, new: {new_sku}'

    def validate(self, result):
        _, change_data = result.change_data()
        changes = change_data['changes']
        if changes.get('sku') and 'sku' not in self.settings.get('ignore_additional_changes', []):
            old_val, new_val = changes.get('sku')
            if old_val.lower() != new_val.lower() and old_val:
                yield ValidationError(self.code, self.msg.format(product=result.old_element['identifier'],
                                                                 old_sku=old_val,
                                                                 new_sku=new_val))
