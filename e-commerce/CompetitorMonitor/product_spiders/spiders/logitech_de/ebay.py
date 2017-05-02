"""
Original ticket: https://www.assembla.com/spaces/competitormonitor/tickets/4462
eBay spider for Demo M account
"""

from product_spiders.base_spiders import BaseeBaySpider
import os

HERE = os.path.abspath(os.path.dirname(__file__))


class DemoMeBaySpider(BaseeBaySpider):
    name = 'demo-m-ebay'
    allowed_domains = ['ebay.de']
    
    def __init__(self, *args, **kwargs):
        super(DemoMeBaySpider, self).__init__(*args, **kwargs)
        self._ebay_url = 'http://www.ebay.de/'
        self._csv_file = os.path.join(HERE, 'logitech_products.csv')
        self._search_fields = ['MPN', 'Brand']
        self._search_criteria = self.EXT_ANY_ORDER
        self._search_in_desc = True
        self._match_fields = ['sku']
        self._meta_fields = [('sku', 'MPN')]
        self._search_in_options = False
        self._check_valid_item = self.check_item
        self._check_diff_ratio = False
        self._search_params = {'_sop': '2',
                                '_fss': '1',
                                '_rusck': '1',
                                '_sacat': '0',
                                '_from': 'R40',
                                'LH_BIN': '1',
                                'LH_ItemCondition': '',
                                'rt': 'nc'}
        
    def check_item(self, item, response):
        self.errors = []
        price = item.get_output_value('price')
        if not price:
            return False
        item.replace_value('brand', 'Logitech')
        return True
    