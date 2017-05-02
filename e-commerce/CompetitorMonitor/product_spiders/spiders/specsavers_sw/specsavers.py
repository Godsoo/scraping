# -*- coding: utf-8 -*-
import shutil
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import HtmlResponse, Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin
from urllib import urlencode
import json
import os
import csv
from datetime import datetime, timedelta
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader

here = os.path.abspath(os.path.dirname(__file__))

from scrapy.item import Item, Field


class SpecMeta(Item):
    Lenses = Field()
    Lens_type = Field()


class SpecSavers(BaseSpider):
    name = "specsavers_sw-specsavers.se"
    allowed_domains = ["specsavers.se"]
    
    def start_requests(self):
        with open(os.path.join(here, 'data.csv')) as f:
            reader = csv.reader(f)
            for row in reader:
                brand = row[0].decode('utf-8')
                name = row[1].replace('-', ' ').decode('utf-8')
                url = row[2].decode('utf-8')
                lenses = row[3]
                lens_type = row[4]
                loader = ProductLoader(item=Product(), selector=HtmlXPathSelector())
                loader.add_value('name', name)
                loader.add_value('identifier', url)
                loader.add_value('url', url)
                loader.add_value('brand', brand)
                meta = SpecMeta()
                meta['Lenses'] = lenses
                meta['Lens_type'] = lens_type

                self.log('product url: %s' % url)
                yield Request(url, meta={'m': meta, 'loader': loader}, dont_filter=True)

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        loader = response.meta['loader']
        meta = response.meta['m']
        price = hxs.select('//span[@class="price-now"]/text()')
        loader.add_value('price', price.extract()[0].replace(',00', ''))
        p = loader.load_item()
        p['metadata'] = meta
        yield p