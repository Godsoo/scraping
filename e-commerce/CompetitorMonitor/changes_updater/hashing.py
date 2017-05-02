import string
import unicodedata
import sys
import base64

table = string.maketrans("", "")

u_table = dict.fromkeys(i for i in xrange(sys.maxunicode)
                        if unicodedata.category(unichr(i)).startswith('P') or
                        unicodedata.category(unichr(i)).startswith('Cc'))


def normalize(s):
    if not s:
        return ''
    elif isinstance(s, unicode):
        return s.translate(u_table).lower().strip()
    else:
        return s.translate(table, string.punctuation).lower().strip()


class ProductHash(object):
    """Class to generate a hashes for products without considering the identifier"""

    hash_fields = ['name', 'category', 'brand', 'dealer', 'sku', 'url']
    identifier_check = ['sku', 'url']

    @classmethod
    def hash(self, product):
        identifier = normalize(product['identifier'])
        fields = []
        for field in self.hash_fields:
            product_field = normalize(product[field])
            if field not in self.identifier_check or identifier not in product_field:
                fields.append(product_field)
            else:
                fields.append(product_field.replace(identifier, ''))

        return ':'.join(fields)
