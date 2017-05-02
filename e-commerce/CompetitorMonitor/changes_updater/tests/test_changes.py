import unittest

from ..changes import PriceChange, MetadataChange, AdditionalChange, IdentifierChange
import json


class TestPriceChange(unittest.TestCase):
    def setUp(self):
        self.attributes = ['identifier', 'name', 'url', 'price',
                           'old_price', 'status', 'sku', 'category',
                           'brand', 'image_url', 'shipping_cost', 'stock', 'dealer']

        self.first_product = {'identifier': '1', 'name': 'p1', 'url': 'u1', 'price': '10',
                               'sku': 's1', 'category': 'c1', 'brand': 'b1', 'image_url': 'iu1',
                               'shipping_cost': '1.00', 'stock': '1', 'dealer': 'd1'}

        self.second_product = {'identifier': '1', 'name': 'p2', 'url': 'u2', 'price': '10',
                               'sku': 's2', 'category': 'c2', 'brand': 'b2', 'image_url': 'iu2',
                               'shipping_cost': '1.00', 'stock': '1', 'dealer': 'd2'}

    def test_no_change(self):
        p = PriceChange(self.first_product, self.second_product)
        self.assertEqual(p.change_data(), (p.NO_CHANGE, {}))
        self.assertEqual('', p.format_csv())

    def test_price_change(self):
        self.second_product['price'] = '20'
        res = {k: self.second_product[k] for k in self.second_product}
        res['old_price'] = '10'
        p = PriceChange(self.first_product, self.second_product)
        res['status'] = p.UPDATE
        self.assertEqual(p.change_data(), (p.UPDATE, res))
        change_data = p.change_data()[1]
        res = ','.join([change_data[a] if a != 'status' else 'updated' for a in self.attributes])
        self.assertEqual(p.format_csv(), res)

    def test_old(self):
        p = PriceChange(self.first_product, None)
        res = {k: self.first_product[k] for k in self.first_product}
        res['status'] = p.OLD
        res['old_price'] = ''
        self.assertEqual(p.change_data(), (p.OLD, res))
        change_data = p.change_data()[1]
        res = ','.join([change_data[a] if a != 'status' else 'old' for a in self.attributes])
        self.assertEqual(p.format_csv(), res)

    def test_new(self):
        p = PriceChange(None, self.second_product)
        res = {k: self.second_product[k] for k in self.second_product}
        res['status'] = p.NEW
        res['old_price'] = ''
        self.assertEqual(p.change_data(), (p.NEW, res))
        change_data = p.change_data()[1]
        res = ','.join([change_data[a] if a != 'status' else 'new' for a in self.attributes])
        self.assertEqual(p.format_csv(), res)

    def test_no_change_price_different_format(self):
        self.first_product['price'] = ''
        self.second_product['price'] = '0'
        p = PriceChange(self.first_product, self.second_product)
        self.assertEqual(p.change_data(), (p.NO_CHANGE, {}))
        self.assertEqual('', p.format_csv())

    def test_silent_update(self):
        self.first_product['price'] = '1'
        self.second_product['price'] = '0'
        p = PriceChange(self.first_product, self.second_product, {'silent_updates': True})
        change_data = p.change_data()[1]
        res = ','.join([change_data[a] if a != 'status' else 'normal' for a in self.attributes])
        self.assertEqual(res, p.format_csv())
        self.first_product['price'] = '0'
        self.second_product['price'] = '1'
        p = PriceChange(self.first_product, self.second_product, {'silent_updates': True})
        change_data = p.change_data()[1]
        res = ','.join([change_data[a] if a != 'status' else 'normal' for a in self.attributes])
        self.assertEqual(res, p.format_csv())

    def test_silent_update_disabled(self):
        self.first_product['price'] = '1'
        self.second_product['price'] = '0'
        p = PriceChange(self.first_product, self.second_product, {'silent_updates': False})
        change_data = p.change_data()[1]
        res = ','.join([change_data[a] if a != 'status' else 'updated' for a in self.attributes])
        self.assertEqual(res, p.format_csv())

class TestMetadataChange(unittest.TestCase):
    def setUp(self):
        self.first_meta = {'attr': '1'}
        self.second_meta = {'attr': '2'}
        self.first_product = {'identifier': '1', 'name': 'p1', 'url': 'u1', 'price': '10',
                               'sku': 's1', 'category': 'c1', 'brand': 'b1', 'image_url': 'iu1',
                               'shipping_cost': '1.00', 'stock': '1', 'dealer': 'd1', 'metadata': self.first_meta}

        self.second_product = {'identifier': '1', 'name': 'p2', 'url': 'u2', 'price': '10',
                               'sku': 's2', 'category': 'c2', 'brand': 'b2', 'image_url': 'iu2',
                               'shipping_cost': '1.00', 'stock': '1', 'dealer': 'd2', 'metadata': self.second_meta}

    def test_no_change(self):
        self.second_product['metadata'] = self.first_meta
        p = MetadataChange(self.first_product, self.second_product)
        self.assertEqual(p.change_data(), (p.NO_CHANGE, {}))
        self.assertEqual('', p.format_json())

    def test_simple_change(self):
        p = MetadataChange(self.first_product, self.second_product)
        change = {'name': self.second_product['name'],
                  'url': self.second_product['url'],
                  'sku': self.second_product['sku'],
                  'identifier': self.second_product['identifier'],
                  'new_metadata': {'attr': '2'}}
        self.assertEqual(p.change_data(), (p.UPDATE, change))
        self.assertEqual(json.loads(json.dumps(change)), json.loads(p.format_json()))

    def test_new_product(self):
        p = MetadataChange(el_new=self.second_product)
        change = {'name': self.second_product['name'],
                  'url': self.second_product['url'],
                  'sku': self.second_product['sku'],
                  'identifier': self.second_product['identifier'],
                  'new_metadata': {'attr': '2'}}
        self.assertEqual(p.change_data(), (p.UPDATE, change))
        self.assertEqual(json.loads(json.dumps(change)), json.loads(p.format_json()))

    def test_old_product_no_change(self):
        p = MetadataChange(el_old=self.second_product)
        self.assertEqual(p.change_data(), (p.NO_CHANGE, {}))

    def test_merge_reviews_by_review_id(self):
        reviews1 = [{'review_id': '1'}, {'review_id': '2'}]
        reviews2 = [{'review_id': '1'}, {'review_id': '3'}]
        self.first_product['metadata']['reviews'] = reviews1
        self.second_product['metadata']['reviews'] = reviews2
        p = MetadataChange(self.first_product, self.second_product)
        p.merge_reviews()

        self.assertItemsEqual(p.new_element['metadata']['reviews'],
                              [{'review_id': '1'}, {'review_id': '2'}, {'review_id': '3'}])

    def test_merge_reviews_by_attributes(self):
        reviews1 = [{'sku': 'sku', 'rating': '1', 'full_text': 'text', 'date': 'd', 'url': 'b'}]
        reviews2 = [{'sku': 'sku', 'rating': '1', 'full_text': 'text', 'date': 'd', 'url': 'a'}]
        self.first_product['metadata']['reviews'] = reviews1
        self.second_product['metadata']['reviews'] = reviews2
        p = MetadataChange(self.first_product, self.second_product)
        p.merge_reviews()

        self.assertItemsEqual(p.new_element['metadata']['reviews'],
                              [{'sku': 'sku', 'rating': '1', 'full_text': 'text', 'date': 'd', 'url': 'a'}])

    def test_change_new_after_delisted(self):
        change = {'name': self.second_product['name'],
                  'url': self.second_product['url'],
                  'sku': self.second_product['sku'],
                  'identifier': self.second_product['identifier'],
                  'new_metadata': {'attr': '1'}}
        self.second_product['metadata'] = self.first_meta
        self.first_product['_status'] = 'old'
        p = MetadataChange(self.first_product, self.second_product)

        self.assertEqual(p.change_data(), (p.UPDATE, change))
        self.assertEqual(json.loads(json.dumps(change)), json.loads(p.format_json()))

class TestAdditionalChange(unittest.TestCase):
    def setUp(self):
        self.first_product = {'identifier': '1', 'name': 'p1', 'url': 'u1', 'price': '10',
                               'sku': 's1', 'category': 'c1', 'brand': 'b1', 'image_url': 'iu1',
                               'shipping_cost': '1.00', 'stock': '1', 'dealer': 'd1'}

        self.second_product = {'identifier': '1', 'name': 'p2', 'url': 'u2', 'price': '10',
                               'sku': 's2', 'category': 'c2', 'brand': 'b2', 'image_url': 'iu2',
                               'shipping_cost': '2.00', 'stock': '2', 'dealer': 'd2'}

    def test_no_change(self):
        p = AdditionalChange(self.first_product, self.first_product)
        self.assertEqual(p.change_data(), (p.NO_CHANGE, {}))
        self.assertEqual('', p.format_json())

    def test_simple_changes(self):
        p = AdditionalChange(self.first_product, self.second_product, settings={'additional_fields': []})
        change = {'product_data': self.first_product,
                  'changes': {'name': (self.first_product['name'], self.second_product['name']),
                              'sku': (self.first_product['sku'], self.second_product['sku']),
                              'url': (self.first_product['url'], self.second_product['url']),
                              'brand': (self.first_product['brand'], self.second_product['brand']),
                              'category': (self.first_product['category'], self.second_product['category']),
                              'image_url': (self.first_product['image_url'], self.second_product['image_url']),
                              'shipping_cost': (self.first_product['shipping_cost'],
                                                self.second_product['shipping_cost']),
                              'dealer': (self.first_product['dealer'], self.second_product['dealer']),
                              'stock': (self.first_product['stock'], self.second_product['stock'])}}
        self.assertEqual(p.change_data(), (p.UPDATE, change))
        self.assertEqual(json.loads(json.dumps(change)), json.loads(p.format_json()))

    def test_new_product_no_change(self):
        p = AdditionalChange(el_new=self.second_product)
        self.assertEqual(p.change_data(), (p.NO_CHANGE, {}))
        self.assertEqual('', p.format_json())

    def test_old_product_no_change(self):
        p = AdditionalChange(el_old=self.second_product)
        self.assertEqual(p.change_data(), (p.NO_CHANGE, {}))
        self.assertEqual('', p.format_json())

    def test_disable_name_change(self):
        p = AdditionalChange(self.first_product, self.second_product,
                             settings={'additional_fields':
                                           ['identifier', 'url', 'shipping_cost', 'sku',
                                            'brand', 'category', 'image_url', 'stock', 'dealer']})

        change = {'product_data': self.first_product,
                  'changes': {'sku': (self.first_product['sku'], self.second_product['sku']),
                              'url': (self.first_product['url'], self.second_product['url']),
                              'brand': (self.first_product['brand'], self.second_product['brand']),
                              'category': (self.first_product['category'], self.second_product['category']),
                              'image_url': (self.first_product['image_url'], self.second_product['image_url']),
                              'shipping_cost': (self.first_product['shipping_cost'],
                                                self.second_product['shipping_cost']),
                              'dealer': (self.first_product['dealer'], self.second_product['dealer']),
                              'stock': (self.first_product['stock'], self.second_product['stock'])}}
        self.assertEqual(p.change_data(), (p.UPDATE, change))
        self.assertEqual(json.loads(json.dumps(change)), json.loads(p.format_json()))

    def test_not_update_to_empty_brand(self):
        second_product = self.second_product.copy()
        second_product['brand'] = ''

        p = AdditionalChange(self.first_product, second_product,
                             settings={'additional_fields': ['brand']})

        change = {}
        self.assertEqual(p.change_data(), (p.NO_CHANGE, change))

    def test_not_update_to_empty_brand2(self):
        second_product = self.second_product.copy()
        second_product['brand'] = ''

        p = AdditionalChange(self.first_product, second_product,
                             settings={'additional_fields': ['brand', 'category']})

        change = {'product_data': self.first_product,
                  'changes': {'category': (self.first_product['category'], self.second_product['category'])}}

        self.assertEqual(p.change_data(), (p.UPDATE, change))
        self.assertEqual(json.loads(json.dumps(change)), json.loads(p.format_json()))

    def test_not_update_to_empty_brand_spaces(self):
        second_product = self.second_product.copy()
        second_product['brand'] = '  '

        p = AdditionalChange(self.first_product, second_product,
                             settings={'additional_fields': ['brand']})

        change = {}
        self.assertEqual(p.change_data(), (p.NO_CHANGE, change))
        
    def test_change_use_latest_price(self):
        self.second_product['price'] = '11'
        p = AdditionalChange(self.first_product, self.second_product, settings={'additional_fields': []})
        p.change_data()
        self.assertEqual(p.change['product_data']['price'], '11')


class TestIdentifierChange(unittest.TestCase):
    def setUp(self):
        self.first_product = {'identifier': '1', 'name': 'p1', 'url': 'u1', 'price': '10',
                               'sku': 's1', 'category': 'c1', 'brand': 'b1', 'image_url': 'iu1',
                               'shipping_cost': '1.00', 'stock': '1', 'dealer': 'd1'}

        self.second_product = {'identifier': '2', 'name': 'p2', 'url': 'u2', 'price': '10',
                               'sku': 's2', 'category': 'c2', 'brand': 'b2', 'image_url': 'iu2',
                               'shipping_cost': '2.00', 'stock': '2', 'dealer': 'd2'}

    def test_no_change(self):
        p = IdentifierChange(self.first_product, self.first_product)
        self.assertEqual(p.change_data(), (p.NO_CHANGE, {}))

    def test_change(self):
        p = IdentifierChange(self.first_product, self.second_product)
        self.assertEqual(p.change_data(), (p.UPDATE, {'old_identifier': '1', 'new_identifier': '2'}))