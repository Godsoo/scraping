import os
import csv

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from navicoitem import NavicoMeta

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


HERE = os.path.abspath(os.path.dirname(__file__))


class DefenderSpider(BaseSpider):
    name = 'navico-amer-defender.com'
    allowed_domains = ['defender.com']
    start_urls = ['http://www.defender.com/']

    rotate_agent = True

    def start_requests(self):
        with open(os.path.join(HERE, 'navico_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = 'http://search.defender.com/search.aspx?expression=%s&x=0&y=0&PageSize=100' % row['code']
                yield Request(url, dont_filter=True, meta={'search_item': row})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        products = hxs.select('//div[@id="divProducts"]//tr/td/a[contains(@id, "pProductsList")]/@href').extract()
        for product in products:
            yield Request(urljoin_rfc(base_url, product), dont_filter=True, callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        search_item = response.meta['search_item']

        sku = ''.join(hxs.select('//span[@itemprop="model"]/text()').extract()).strip()
        name = ''.join(hxs.select('//span[@itemprop="name"]/text()').extract())
        if sku.upper().strip() == search_item['code'].upper().strip() and search_item['brand'].upper().strip() in name.upper().strip():
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('name', name)
            loader.add_value('url', response.url)
            loader.add_value('sku', search_item['code'])
            loader.add_value('brand', search_item['brand'])
            image_url =  hxs.select('//img[@itemprop="image"]/@src').extract()
            image_url = urljoin_rfc(base_url, image_url[0]) if image_url else ''
            loader.add_value('image_url', image_url)
            identifier = hxs.select('//input[@id="productNumber"]/@value').extract()
            if not identifier:
                self.log('Product without identifier: ' + response.url)
                return
            identifier = identifier[0]
            loader.add_value('identifier', identifier)

            category = search_item['category']
            if not category:
                category = hxs.select('//div[@id="containerBreadcrunmtrail"]//a/text()').extract()

            loader.add_value('category', search_item['brand'])
            loader.add_value('category', category)
            price = hxs.select('//*[@itemprop="price"]/text()').extract()
            loader.add_value('price', price)
            prod = loader.load_item()
            metadata = NavicoMeta()
            metadata['screen_size'] = search_item['screen size']
            prod['metadata'] = metadata

            yield prod
        else:
            if name:
                self.log('Invalid brand or code: ' + response.url)
