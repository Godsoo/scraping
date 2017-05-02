# -*- coding: utf-8 -*-
import csv

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import FormRequest, Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc
from datetime import datetime
import os
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

HERE = os.path.abspath(os.path.dirname(__file__))


class MandpSpider(BaseSpider):
    name = u'mandp.co.uk_ids'
    allowed_domains = ['www.mandp.co.uk']
    run_type = ''

    def start_requests(self):
        current_ids = set()
        ids = set()
        with open(os.path.join(HERE, 'mandp.csv')) as f:
            reader = csv.DictReader(f)
            for r in reader:
                current_ids.add(r['identifier'])

        with open(os.path.join(HERE, 'mandp_products.csv')) as f:
            reader = csv.reader(f)
            for r in reader:
                if r[0] not in current_ids:
                    ids.add(r[0])

        self.log('%s products to parse' % len(ids))
        for identifier in ids:
            yield Request('http://www.mandp.co.uk/productInfo.aspx?catRef={}'.format(identifier.strip()),
                          callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        identifier = hxs.select('//*[@id="ctl00_pnlContent"]/table[2]/tr/td[2]/table/tr/td[1]/text()[1]').extract()
        if not identifier:
            return
        identifier = identifier[0].replace('Code:', '').strip()
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        name = hxs.select('//*[@id="ctl00_ContentPlaceHolder1_lblCategoryTitle"]/text()').extract()[0].strip()
        url = '/productinfo.aspx?catref={}'.format(identifier)
        loader.add_value('url', urljoin_rfc(base_url, url))
        loader.add_value('name', name)
        image_url = hxs.select('//*[@id="mainPhoto"]/@href').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        category = hxs.select('//*[@id="ctl00_hyperlink1"]/text()').extract()
        if category:
            loader.add_value('category', category[0])
        price = hxs.select('//*[@id="ctl00_ContentPlaceHolder1_lblPrice"]/text()').extract()
        if not price:
            price = hxs.select('//*[@id="ctl00_ContentPlaceHolder1_lblPrice"]/font[1]/text()').extract()
        price = extract_price(price[0])
        loader.add_value('price', price)
        brand = hxs.select('//*[@id="ctl00_hyperlink3"]/text()').extract()
        if brand:
            loader.add_value('brand', brand[0])
        product = loader.load_item()

        yield product