from . import Validator, ValidationError
from ..changes import Change


class ImmutableMetadataValidator(Validator):
    accept_codes = [Change.UPDATE]
    code = 16
    msg = u'Immutable metadata field has changed. Product: {product} | Field: {field} | ' \
          u'Old: {old_value}, New: {new_value} <a href="{url}" target="_blank">View Product</a>'

    def validate(self, result):
        _, change_data = result.change_data()
        old_element = result.old_element
        fields = self.settings['immutable_metadata']
        if fields and old_element:
            old_metadata = old_element['metadata']
            fields = fields.split(',')
            if '*' in fields:
                fields = [x for x in old_element['metadata']]
            for field in fields:
                if field in old_metadata:
                    if change_data['new_metadata'] and (field not in change_data['new_metadata'] or
                                    old_element['metadata'][field] != change_data['new_metadata'][field]):
                        yield ValidationError(self.code,
                                              self.msg.format(old_value=old_element['metadata'].get(field, ''),
                                                              new_value=change_data['new_metadata'].get(field, ''),
                                                              field=field,
                                                              product=change_data['identifier'],
                                                              url=change_data['url']))
