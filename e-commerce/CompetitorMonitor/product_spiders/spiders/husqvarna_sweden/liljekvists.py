import re
import json
from decimal import Decimal
from cStringIO import StringIO

from scrapy import log
from scrapy.spider import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from scrapy.item import Item, Field

from product_spiders.items import (
    Product,
    ProductLoaderWithoutSpaces as ProductLoader,
)

from scrapy.http import Request, HtmlResponse


class LiljekvistsSpider(CrawlSpider):
    name = 'husqvarna_sweden-liljekvists.se'
    allowed_domains = ['liljekvists.se', 'liljekvists.com']
    start_urls = ('http://www.liljekvists.se',)
    seen_ids = []
    rules = [
        Rule(LinkExtractor(
            restrict_xpaths='//ul[@id="mainmenu"]',
            restrict_css='.submenu'),
            process_request='process_request'
        )]

    def process_request(self, request):
        match = re.search('\d+$', request.url)
        if not match:
            return request
        url = 'http://www.liljekvists.com/shop.json?pid=%s&sub=1&po=1' %match.group()
        request = request.replace(url=url, callback=self.parse_products)
        return request
    
    def parse_products(self, response):
        data = json.loads(response.body)
        for item in data['items']:
            loader=ProductLoader(item=Product(), response=response)
            loader.add_value('identifier', item['id'])
            loader.add_value('sku', item['id'])
            loader.add_value('name', item['nm'])
            loader.add_value('price', item['p'])
            loader.add_value('url', response.urljoin(item['l']))
            loader.add_value('image_url', response.urljoin(item['img']))
            yield loader.load_item()
                                      
    def __parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//div[@id="navigation"]//a/@href').extract()
        categories += hxs.select('//div[@id="product-navigation"]//a/@href').extract()
        categories += response.xpath('//ul[@id="mainmenu"]//a/@href').extract()
        for url in categories:
            yield Request(urljoin_rfc(base_url, url))

        next_page = hxs.select('//ul[@class="pagination"]/li/a[contains(@title,"sta")]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]))

        products = response.xpath('//div[@class="product-list"]//p/a/@href').extract()
        products += response.xpath('//p[@class="pull-right"]/a[text()="Visa"]/@href').extract()
        for url in set(products):
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)


    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        loader = ProductLoader(item=Product(), response=response)
        # identifier = hxs.select('').extract()
        sku = hxs.select('//p/span[@itemprop="sku"]/text()').extract()
        identifier = sku
        if not sku:
            identifier = response.url.split('/')[-1].split('.')[0]
        loader.add_value('identifier', identifier)
        loader.add_value('sku', sku)
        if identifier in self.seen_ids:
            return
        self.seen_ids.append(identifier)
        name = hxs.select('//h1[@class="first"]/span[@itemprop="name"]/text()').extract()[0].strip()
        try:
            loader.add_value('name', name)
        except:
            loader.add_value('name', name.decode('utf-8', 'replace'))
        category = hxs.select('//ol[@class="breadcrumb"]//a/text()').extract()
        loader.add_value('category', ' > '.join(category[1:][-3:]))
        image_url = hxs.select('//a[@class="lightbox"]/img/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        loader.add_value('url', response.url)
        
        price = hxs.select('//span[@class="price-big orange"]/text()').extract()[0]
        loader.add_value('price', price)
        if not loader.get_output_value('price'):
            loader.add_value('stock', 0)
        yield loader.load_item()
