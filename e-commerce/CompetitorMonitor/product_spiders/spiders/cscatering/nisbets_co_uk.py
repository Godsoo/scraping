import os
import csv
import cStringIO

import re
import json
import urlparse
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest, HtmlResponse
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.base_spiders.primary_spider import PrimarySpider

from phantomjs import PhantomJS
import time

from scrapy import log


class NisbetsSpider(PrimarySpider):
    name = 'nisbets.co.uk'
    allowed_domains = ['nisbets.co.uk']
    start_urls = ('http://www.nisbets.co.uk/Homepage.action',)

    csv_file = 'nisbets_products.csv'

    # NOTE: important to get the first page
    user_agent = 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/32.0.1700.107 Chrome/32.0.1700.107 Safari/537.36'

    _skus = None

    ignore_brands = ['FALCON']

    def start_requests(self):
        browser = PhantomJS()
        url = 'http://www.nisbets.co.uk/Homepage.action'
        self.log('>>> BROWSER: GET => %s' % url)
        browser.get(url)
        self.log('>>> BROWSER: OK')

        time.sleep(120)

        page_source = browser.driver.page_source

        browser.close()

        for req in self.parse(url, page_source):
            yield req

    def map_sku(self, sku):
        if self._skus is None:
            self._skus = dict()
            with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'nisbets.csv')) as f:
                reader = csv.DictReader(cStringIO.StringIO(f.read()))
                for row in reader:
                    if row['Nisbets Code']:
                        self._skus[row['Nisbets Code'].lower()] = row['sku']
        return self._skus.get(sku.lower().strip(), sku)

    def parse(self, base_url, page_source):
        hxs = HtmlXPathSelector(text=page_source)

        for cat in hxs.select('//ul[@class="clear-after"]/li/ul/li/a'):
            yield Request(urljoin_rfc(base_url, cat.select('./@href').extract()[0]), callback=self.parse_cat, meta={'category':cat.select('./text()').extract()[0]})

    def parse_cat(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        subcats = hxs.select('//div[contains(@class,"category-fourgrid") or contains(@class,"sub-category-grid")]//a/@href').extract()
        productsxs = hxs.select('//div[contains(@class,"product-list-row") and div[contains(@class, "product-info")]]')

        if not subcats and not productsxs:
            retry = int(response.meta.get('retry', 0))
            if retry < 10:
                retry += 1
                new_req = response.request.copy()
                new_req.meta['retry'] = retry
                new_req.dont_filter = True
                yield new_req
            return

        for url in subcats:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_cat, meta=response.meta)

        for productxs in productsxs:
            product_options_link = productxs.select('.//div[@class="form-row"]/a/@href').extract()
            if product_options_link:
                yield Request(urljoin_rfc(base_url, product_options_link[0]), callback=self.parse_cat, meta=response.meta)
            else:
                loader = ProductLoader(item=Product(), selector=productxs)
                loader.add_value('price', ''.join(productxs.select('.//div[@class="price"]//text()').extract()))
                if productxs.select('.//img[@alt="In stock" or contains(@alt,"days delivery") or contains(@alt,"Day Delivery") or contains(@alt,"Hour Delivery")]'):
                    loader.add_value('stock', 1)
                else:
                    loader.add_value('stock', 0)
                loader.add_xpath('identifier', './/p[@class="code"]/text()')
                product_url = productxs.select('.//h3[@class="product-name"]/a/@href').extract()[0]
                loader.add_value('url', urljoin_rfc(base_url, product_url))
                loader.add_xpath('name', './/h3[@class="product-name"]/a/text()')
                loader.add_value('category', response.meta.get('category'))
                loader.add_value('sku', self.map_sku(''.join(productxs.select('.//p[@class="code"]/text()').extract())))
                img = productxs.select('.//div[@class="primaryImageDiv"]//img/@src').extract()
                if img:
                    loader.add_value('image_url', urljoin_rfc(base_url, img[0].replace('/medium/', '/large/')))
                loader.add_xpath('brand', './/img[@class="brand-image"]/@alt')
                brand = loader.get_output_value('brand').strip().upper()
                if brand in self.ignore_brands:
                    log.msg('Ignoring %s product: %s' % (brand, response.url))
                    return

                item = self.add_shipping_cost(loader.load_item())

                if item.get('identifier', '').strip():
                    yield item

        for url in hxs.select('//ul[@class="pager"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_cat, meta=response.meta)

    def add_shipping_cost(self, item):
        if item.get('price', 0) < 50:
            item['shipping_cost'] = 5
        else:
            item['shipping_cost'] = 0
        return item
