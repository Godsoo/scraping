# -*- coding: utf-8 -*-
import logging

import csv
import os.path
import re
from decimal import Decimal

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class AntaresElettricSpider(BaseSpider):
    name = 'newbricoman-antareselettric.it'
    allowed_domains = ('antareselettric.it',)
    start_urls = ('http://www.antareselettric.it/',)

    VAT = Decimal('0.21')

    def __init__(self, *args, **kwargs):
        super(AntaresElettricSpider, self).__init__(*args, **kwargs)

        self.rows = []

        with open(os.path.join(HERE, 'bricoman_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.rows.append(row)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        categories = hxs.select("//div[@id='categories']//a[@class='category-links']/@href").extract()
        categories += hxs.select("//div[@id='categories']//a[@class='category-top']/@href").extract()

        for category_url in categories:
            url = urljoin_rfc(get_base_url(response), category_url)

            r = Request(url, callback=self.parse_products_list)
            yield r

    def parse_products_list(self, response):
        hxs = HtmlXPathSelector(response)

        pages = hxs.select("//div[@id='productsListingListingTopLinks']//a/@href").extract()
        for page_url in pages:
            url = urljoin_rfc(get_base_url(response), page_url)

            r = Request(url, callback=self.parse_products_list)
            yield r

        category = hxs.select("//div[@id='navBreadCrumb']/text()[last()]").extract()[0].replace(":", "").strip()
        products = hxs.select("//div[@id='productListing']/table/tr[td[@class='productListing-data']]")
        for p in products:
            name = p.select(".//h3[@class='itemTitle']/a/text()").extract()[0]
            url = p.select(".//h3[@class='itemTitle']/a/@href").extract()[0]
            brand = ''
            image_url = urljoin_rfc(get_base_url(response), p.select(".//img[@class='listingProductImage']/@src").extract()[0])
            sku = p.select("td[1]/text()").extract()[0]
            identifier = re.search("products_id=([^&]*)", url).group(1)
            stock_img_name = p.select(".//td[position() > 1]/img/@alt").extract()[0]
            if stock_img_name == u'Disponibilità alta':
                stock = None
            elif stock_img_name == u'Non disponibile':
                stock = 0
            elif stock_img_name == u'Disponibiltà media':
                stock = None
            elif stock_img_name == u'Disponibiltà bassa':
                stock = None
            else:
                logging.error("ASD. Unknown stock status: %s" % stock_img_name)
                stock = None

            price = p.select("td[last()]/span[@class='productSpecialPrice']/text()").extract()
            if not price:
                price = p.select("td[last()]/span[@class='normalprice']/text()").extract()
            if not price:
                price = p.select("td[last()]/text()").extract()
            price = price[0]
            price = price.replace(".", "").replace(",", ".").replace(u"€", "")

            price = Decimal(price)
            price += price * self.VAT

            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('name', name)
            loader.add_value('url', url)
            loader.add_value('category', category)
            loader.add_value('brand', brand)
            loader.add_value('image_url', image_url)
            loader.add_value('sku', sku)
            loader.add_value('identifier', identifier)
            loader.add_value('stock', stock)
            loader.add_value('price', price)
            loader.add_value('shipping_cost', '9.90')

            yield loader.load_item()
