import re
import json
import urlparse
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.base_spiders.prodcache import ProductCacheSpider

class TheWhiskyExchangeSpider(ProductCacheSpider):
    name = 'thewhiskyexchange.com'
    allowed_domains = ['thewhiskyexchange.com']
    start_urls = ('http://thewhiskyexchange.com',)

    def _start_requests(self):
        yield Request('http://www.thewhiskyexchange.com/C-330.aspx?pg=7', callback=self.parse_cat, meta={'product': Product()})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        categories = hxs.select('//a[@class="panel-item-title"]/@href').extract()
        categories += hxs.select('//a[@class="panel-item-link"]/@href').extract()
        for cat in categories:
            yield Request(urljoin_rfc(get_base_url(response), cat), callback=self.parse_cat)

    def parse_cat(self, response):
        hxs = HtmlXPathSelector(response)
            
        for productxs in hxs.select('//div[@class="item"]'):
            product = Product()

            price = productxs.select('.//span[@class="price"]//text()').extract()
            product['price'] = extract_price(price[0]) if price else 0
            product['name'] = ''.join(productxs.select('.//span[@class="name"]//text()').extract()[0]).strip()
            if not product['name']:
                product['name'] = ''.join(productxs.select('.//div[@class="title"]/a/@title').extract()[0]).strip()
            pid = productxs.select('.//a[@class="product"]/@href').re('(\d+)')
            if not pid:
                pid = productxs.select('.//div[@class="title"]/a/@href').re('(\d+)')
            product['identifier'] = pid[0]
            product['sku'] = product['identifier']
            if product['price']:
                product['stock'] = '1'
            else:
                product['stock'] = '0'

            url = productxs.select('.//a[@class="product"]/@href').extract()
            url = urljoin_rfc(get_base_url(response), url[0])

            request = Request(url, callback=self.parse_product)
            yield self.fetch_product(request, self.add_shipping_cost(product))

        for page in hxs.select('//a[@class="page-link"]/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), page), callback=self.parse_cat)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=response.meta['product'], selector=hxs)

        loader.add_value('url', response.url)
        loader.add_xpath('category', '//ul/li[@itemtype="http://data-vocabulary.org/Breadcrumb" and position()=2]//span/text()')
        if not loader.get_output_value('category'):
            loader.add_value('category', 'Selection')
        img = hxs.select('//div[@id="productDefaultImage"]/img/@data-original').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        loader.add_xpath('brand', '//*[@itemprop="brand"]/@content')
        if not loader.get_output_value('brand'):
            name = response.meta['product']['name']
            loader.add_value('brand', name.split()[0])

        yield self.add_shipping_cost(loader.load_item())

    def add_shipping_cost(self, item):
        item['shipping_cost'] = 4.95
        return item
