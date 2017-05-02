from scrapy.item import Item, Field


class HarveysMeta(Item):
    product_type = Field()
    was_price = Field()

TWO_SEATER = '2 seater'
THREE_SEATER = '3 seater'


def set_product_type(product, additional_terms=None, was_price=None):
    '''
    >>> product = {'name': 'example product 2  seater test'}
    >>> res = set_product_type(product)
    >>> res['metadata']['product_type']
    '2 seater'
    >>> product = {'name': 'example product 3  seater test'}
    >>> res = set_product_type(product)
    >>> res['metadata']['product_type']
    '3 seater'
    >>> product = {'name': 'example product large'}
    >>> res = set_product_type(product, {TWO_SEATER: [], THREE_SEATER: ['large']})
    >>> res['metadata']['product_type']
    '3 seater'
    '''
    name = product['name'].lower()
    words = name.split(' ')
    words = [w for w in words if w]
    product_type = None
    norm_name = ' '.join(words)
    if '2 seater' in norm_name:
        product_type = TWO_SEATER
    elif '3 seater' in norm_name:
        product_type = THREE_SEATER
    elif additional_terms:
        two_seater_terms = additional_terms[TWO_SEATER]
        for term in two_seater_terms:
            if term in norm_name:
                product_type = TWO_SEATER
                break

        if not product_type:
            three_seater_terms = additional_terms[THREE_SEATER]
            for term in three_seater_terms:
                if term in norm_name:
                    product_type = THREE_SEATER
                    break
    meta = HarveysMeta()
    if product_type:
        meta['product_type'] = product_type
    if was_price:
        meta['was_price'] = str(was_price)

    if product_type or was_price:
        product['metadata'] = meta

    return product
