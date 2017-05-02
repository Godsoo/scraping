import re
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoader

import logging
from utils import get_product_list

class MaplinSpider(BaseSpider):
    name = 'maplin.co.uk'
    allowed_domains = ['maplin.co.uk']
    search_url = 'http://www.maplin.co.uk/search?text='

    def start_requests(self):
        for row in get_product_list('Maplins'):
            if row['url']:
                yield Request(row['url'], callback=self.parse_product, meta=row)
            else:
                url = self.search_url + row['search'].pop(0).replace(' ', '+')
                yield Request(url, callback=self.parse_search, meta=row)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        l = ProductLoader(item=Product(), selector=hxs)
        l.add_xpath('identifier', '//*[@itemprop="sku"]/text()')
        l.add_xpath('name', '//h1[@itemprop="name"]/text()')
        l.add_value('url', response.url)
        l.add_xpath('price', '//*[@itemprop="price"]/@content')
        l.add_xpath('image_url', '//*[@itemprop="image"]/@src')
        l.add_value('sku', response.meta['sku'])
        l.add_value('brand', response.meta['brand'])
        l.add_value('category', response.meta['category'])
        l.add_value('stock', re.search('"stock": (.+),', response.body).group(1))
        if l.get_output_value('price') < 10:
            l.add_value('shipping_cost', '2.99')
        else:
            l.add_value('shipping_cost', '0')
        yield l.load_item()

    def parse_search(self, response):
        hxs = HtmlXPathSelector(response)

        # parse pages
        for url in hxs.select('//ul[@class="pagination"]//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_search, meta=response.meta)

        # parse products
        found = False
        for url in hxs.select('//div[@class="titleinfo"]/h3/a/@href').extract():
            found = True
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product, meta=response.meta)

        if not found and response.meta['search']:
            url = self.search_url + response.meta['search'].pop(0).replace(' ', '+')
            yield Request(url, callback=self.parse_search, meta=response.meta)
