import os

from product_spiders.base_spiders import BaseeBaySpider

HERE = os.path.abspath(os.path.dirname(__file__))

class HGolfEbaySpider(BaseeBaySpider):

    name = 'hurricanegolf-ebay.com'

    def __init__(self, *args, **kwargs):
        super(HGolfEbaySpider, self).__init__()
        self._ebay_url = 'http://www.ebay.com/'
        # FIXME: should use main spider's crawl results from `data` folder. See example: `andlingdirect/ebay_co_uk.py`
        self._exclude_sellers = ['hurricane_golf']
        self._search_fields = ['name']
        self._all_vendors = False
        self._meta_fields = [('price', 'price'),
                             ('identifier', 'identifier')]
        self._match_fields = ('identifier',)
        self._limit_pages = 10
        self._converted_price = True  # US$

        self.errors.append("Spider works incorrectly: "
                           "it should use main spider's last crawl results, but uses local file")
