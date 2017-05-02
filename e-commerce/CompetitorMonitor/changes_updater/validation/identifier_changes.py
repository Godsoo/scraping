from . import Validator, ValidationError
from ..changes import Change


class IdentifierChangeValidator(Validator):
    accept_codes = [Change.UPDATE]
    code = 18
    msg = u'Product identifier has changed for product: <i>{product}</i>.' \
          u'Old identifier: <b>{old_identifier}</b> (<a href="{old_url}" target="_blank">Old URL</a>),' \
          u'New identifier: <b>{new_identifier}</b> (<a href="{new_url}" target="_blank">New URL</a>).'

    def validate(self, result):
        _, change_data = result.change_data()
        old_element = result.old_element
        new_element = result.new_element
        if new_element['status'] in ['new', 'normal']:
            yield ValidationError(self.code, self.msg.format(product=new_element['name'],
                                                             old_identifier=old_element['identifier'],
                                                             old_url=old_element['url'],
                                                             new_identifier=new_element['identifier'],
                                                             new_url=new_element['url']),
                                  new_element=new_element, old_element=old_element)
