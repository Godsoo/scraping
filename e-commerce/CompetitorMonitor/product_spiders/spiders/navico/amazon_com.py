# coding=utf-8
__author__ = 'juraseg'

from product_spiders.base_spiders.amazonspider2.amazonspider import BaseAmazonSpider

class NavicoAmazonComSpiser(BaseAmazonSpider):
    name = 'navico_amazon.com'
    type = 'asins'
    domain = 'amazon.com'
    only_buybox = True

    use_amazon_identifier = False

    asins = ['B00AU5T6B4', 'B00FPQWQQK']

    def get_asins_generator(self):
        for asin in self.asins:\
            yield asin, ''