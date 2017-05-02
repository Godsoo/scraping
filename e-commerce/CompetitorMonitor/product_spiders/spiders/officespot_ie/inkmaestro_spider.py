import os
import re
import json
import csv
import urlparse

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from scrapy import log

from utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class InkMaestroSpider(BaseSpider):
    name = 'inkmaestro.ie'
    allowed_domains = ['inkmaestro.ie', '123ink.ie']

    start_urls = ['http://www.123ink.ie/']

    def start_requests(self):
        with open(os.path.join(HERE, 'officespot_codes.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                meta = {'sku': row['Product Code'], 'MfrPartNum': row['MfrPartNum']}
                if row['Type'] == 'compatibles':
                    url = 'https://www.123ink.ie/search/?search=' + row['MfrPartNum']
                    meta['ignore_original'] = True
                else:
                    url = 'https://www.123ink.ie/search/?search=' + row['Barcode']
                yield Request(url, dont_filter=True, callback=self.parse_search, meta=meta)


    def parse_search(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        meta = response.meta
        if meta.get('ignore_original', False):
            products = hxs.select('//td[@class="prodlink"]/a[not(contains(@href, "-original-"))]/@href').extract()
        else:
            products = hxs.select('//td[@class="prodlink"]/a/@href').extract()

        if products:
            yield Request(products[0], meta=meta)
        '''
        else:
           if not meta.get('partnum_search', False) and not meta.get('ignore_original', False):
               url = 'https://www.inkmaestro.ie/search/?search='+meta.get('MfrPartNum')
               meta['partnum_search'] = True
               yield Request(url, callback=self.parse_search, meta=meta)
        '''

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        meta = response.meta
        eol = hxs.select('//div[@class="prodspecs"]//form[@action="' + response.url + '"]/span[@class="eol"]').extract()
        if not eol:
            l = ProductLoader(item=Product(), response=response)
            name = hxs.select('//*[@itemprop="name"]/text()').extract()[0]
            if meta.get('ignore_original', False):
                if 'Digital Revolution'.upper() not in name.upper():
                    return
            l.add_value('name', name)
            l.add_value('url', response.url)
            l.add_value('sku', meta.get('sku'))
            l.add_value('identifier', meta.get('sku'))
            brand = ''.join(hxs.select('//div[@itemtype="http://data-vocabulary.org/Product"][1]//tr[td/span[contains(text(), "Brand")] or td[contains(text(), "Brand")]]/td//text()').extract())
            if 'BRAND' in brand.upper():
                brand = brand.split('Brand:')[-1].strip()
            else:
                brand = ''

            l.add_value('brand', brand)
            image_url = hxs.select('//div[@class="prodspecs"]//img/@src').extract()
            image_url = urljoin_rfc(base_url, image_url[0]) if image_url else ''
            l.add_value('image_url', image_url)
            category = hxs.select('//ul[@class="breadcrumb"]/li/a/span/text()').extract()[1]
            l.add_value('category', category)
            price = re.search(' (.*) Excluding', response.body)
            price = extract_price(price.group(1)) if price else 0
            l.add_value('price', price)
            if price > 50:
                l.add_value('shipping_cost', 2.40)
            else:
                l.add_value('shipping_cost', 3.21)
            yield l.load_item()
        else:
            log.msg('Ignores product EOL ' + response.url)
