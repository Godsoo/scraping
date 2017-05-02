# -*- coding: utf-8 -*-

__author__ = 'Theophile R. <rotoudjimaye.theo@gmail.com>'


from .kikkertland_dk import SpiderTemplate

class JaqmarkedSpider(SpiderTemplate):
    name = "jagtmarked.dk"
    allowed_domains = ["jagtmarked.dk"]
    start_urls = ["http://www.jagtmarked.dk/"]

    THOUSAND_SEP = "."
    DECIMAL_SEP = ","

    CHECK_PRICE_IN_PRODUCT_PAGE = True

    PRODUCT_URL_EXCLUDE = ('/group.asp', '/basket.asp', '/info.asp', '/login.asp')
    NAV_URL_EXCLUDE = ('/info.asp', '/login.asp')

    NAVIGATION = [
        '//td[@id="shopmenu"]//a/@onclick', '//td[@id="shopmenu"]//tr/@onclick'
    ]
    #['//a/@href']

    PRODUCT_BOX = [
        ('//td[@id="group"]', {'name': './font/a/b/text()', 'url': './/a/@href', 'price': ['.//font[@id="offer"]/text()', './font/b[2]/text()', './/span[@class="price"]/text()']}),
        ('.', {'name': '//b[@id="header"]/text()', 'price': ['//td[@id="productdata"]/font/b/text()', '//font[@id="offer"]/text()']}),
    ]

    def preprocess_link(self, href):
        return href.split("'")[1] if "'" in href else href
