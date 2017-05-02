import os

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

import csv

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy import log

HERE = os.path.abspath(os.path.dirname(__file__))

class Toys4CarsSpider(BaseSpider):
    name = 'towequipe-toys4cars.co.uk'
    allowed_domains = ['toys4cars.co.uk', 'www.toys4cars.co.uk']
    start_urls = (u'http://www.toys4cars.co.uk',)

    def start_requests(self):
        with open(os.path.join(HERE, 'products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                sku = row['SKU']
                url = u'http://www.toys4cars.co.uk/catalogsearch/result/?q=%(q)s'
                yield Request(url % {'q': sku}, meta={'sku': sku, 'partn': row['partn'], 'postage': float(row['toys4cars_postage'])})

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        products = hxs.select(u'//div[@class="product-shop"]')
        if products:
            meta = response.meta
            meta['next_results'] = []
            next_page = hxs.select(u'//a[@class="next i-next"]/@href').extract()
            for product in products:
                url = urljoin_rfc(base_url, product.select(u'.//*[@class="product-name"]/a/@href')[0].extract())
                yield Request(url, callback=self.parse_product, meta=meta,
                              dont_filter=True)
            if next_page:
                yield Request(urljoin_rfc(base_url, next_page.pop().strip()),
                              callback=self.parse,
                              meta=meta,
                              dont_filter=True)

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        name = hxs.select(u'//div[@class="page-title"]/h1/text()')[0].extract().strip()

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_value('name', name)
        loader.add_value('url', response.url)
        loader.add_xpath('image_url', u'//div[@class="product-image"]//img/@src')
        base_price = hxs.select(u'//span[@class="price"]/text()')
        if base_price:
            base_price = base_price[0].extract()
        else:
            base_price = u'0.00'
        base_price = base_price.replace(u'\xa3', '').strip()
        base_price = float(base_price) + response.meta['postage']
        loader.add_value('price', base_price)
        sku = hxs.select('//div[@id="product_tabs_custom_contents"]'
                         '/div[@class="product-specs"]/text()')[0].extract().strip()
        log.msg('SKU: [%s == %s]' % (sku.lower(), response.meta['sku'].lower()))
        if sku.lower() == response.meta['sku'].lower():
            loader.add_value('sku', response.meta['partn'])
            loader.add_value('identifier', response.meta['partn'].lower())
            yield loader.load_item()
