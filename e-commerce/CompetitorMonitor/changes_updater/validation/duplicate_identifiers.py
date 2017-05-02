from . import ValidationError


class DuplicateIdentifierValidator(object):
    code = 6
    msg = u'Duplicate identifier found for product: <i>{identifier}</i>.'
    previous_identifier = None

    def validate(self, product):
        ident = self.previous_identifier
        self.previous_identifier = product['identifier']

        if ident == product['identifier']:
            return ValidationError(self.code, self.msg.format(identifier=product['identifier']))
