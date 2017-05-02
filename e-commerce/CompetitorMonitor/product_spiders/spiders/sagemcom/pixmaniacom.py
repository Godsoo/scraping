# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
    )

import logging


class PixmaniaSagemcomSpider(BaseSpider):
    name = "pixmania.co.uk_sagemcom"
    allowed_domains = ["pixmania.co.uk"]
    start_urls = (
        'http://www.pixmania.co.uk/uk/uk/12647589/art/sagemcom/rti-95-320-freeview-hd-re.html',
        'http://www.pixmania.co.uk/uk/uk/12703516/art/sagemcom/rti95-500-freeview-hd-rec.html',
        'http://www.pixmania.co.uk/uk/uk/6214389/art/sagemcom/dtr94320t-freesat-hd-digi.html',
        'http://www.pixmania.co.uk/uk/uk/2972499/art/sagemcom/dtr-67320t-eco-digital-tv.html',
        'http://www.pixmania.co.uk/uk/uk/12727207/art/philips/hdtp-8530-freeview-hd-rec.html',
        )

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), selector=hxs)

        name = hxs.select("//div[contains(@class, 'prd-name')]/h1/span/text()").extract()
        if not name:
            logging.error("No name! %s" % response.url)
            return
        name = name[0]

        price = hxs.select("//p[contains(@class, 'prd-amount')]//span[contains(@class, 'prd-price')]//text()").extract()
        if not price:
            logging.error("No price! %s" % response.url)
            return
        price = "".join(price)

        loader.add_value('name', name)
        loader.add_value('url', response.url)
        loader.add_value('price', self._encode_price(price))
        yield loader.load_item()

    def _encode_price(self, price):
        return price.replace(',', '.').encode("ascii", "ignore")
