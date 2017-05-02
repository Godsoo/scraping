import csv
import os

import re
import urlparse
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.base_spiders.prodcache import ProductCacheSpider
import datetime


def normalize_space(s):
    ''' Cleans up space/newline characters '''
    return re.sub(r'\s+', ' ', s.replace(u'\xa0', ' ').strip())

HERE = os.path.abspath(os.path.dirname(__file__))

class SkinfantasticSpider(ProductCacheSpider):
    name = 'skinfantastic.co.uk'
    allowed_domains = ['skinfantastic.co.uk']
    start_urls = ['http://www.skinfantastic.co.uk/']

    def _start_requests(self):
        yield Request('http://www.skinfantastic.co.uk/Agera/', callback=self.parse_cat)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for url in response.css('.HomeCatBox a::attr(href)').extract():
            yield Request(response.urljoin(url), callback=self.parse_cat)

    def parse_cat(self, response):
        hxs = HtmlXPathSelector(response)

        sub_categories = response.css('.sf-subcat a::attr(href)').extract()
        sub_categories += response.xpath('//div[@id="MainCats"]//a/@href').extract()
        for sub_cat in sub_categories:
            yield Request(response.urljoin(sub_cat), callback=self.parse_cat)

        for productxs in response.css('.ProdListItem'):
            product = Product()
            product['price'] = extract_price(productxs.css('.ProdListPrice .currency ::text').extract_first())
            if product['price'] == 0:
                product['stock'] = '0'
            else:
                product['stock'] = '1'
            url = productxs.xpath('.//h2/a/@href').extract_first()
            request = Request(response.urljoin(url), callback=self.parse_product, meta=response.meta)
            yield self.fetch_product(request, self.add_shipping_cost(product))
        
        for page in response.xpath('//div[@class="nav-pages"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), page), callback=self.parse_cat)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=response.meta['product'], selector=hxs)

        loader.add_value('url', response.url)
        loader.add_xpath('identifier', '//input[@name="productid"]/@value')
#        loader.add_value('sku', response.url.split('/')[-1][:-5])
        loader.add_xpath('sku', '//input[@name="productid"]/@value')
        loader.add_value('name', normalize_space(' '.join(hxs.select('//div[@class="dialog"]//h2/span/text()').extract())))
        loader.add_xpath('category', '//div[@id="location"]/a[position()>1]/text()')
        img = hxs.select('//img[@id="product_thumbnail"]/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        loader.add_xpath('brand', '//div[@id="location"]/a[2]/text()')
        if not loader.get_output_value('category'):
            loader.add_value('category', normalize_space(' '.join(hxs.select('//div[@class="dialog"]//h2/span[@style="color:#c7adc7;"]/text()').extract())))
            loader.add_value('brand', normalize_space(' '.join(hxs.select('//div[@class="dialog"]//h2/span[@style="color:#c7adc7;"]/text()').extract())))

        yield self.add_shipping_cost(loader.load_item())

    def add_shipping_cost(self, item):
        return item
