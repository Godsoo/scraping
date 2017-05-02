import csv
import os
import copy

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from utils import extract_price_eu

class MaxiToysSpider(BaseSpider):
    name = 'legofrance-maxitoys.fr'
    allowed_domains = ['maxitoys.fr']
    start_urls = ('http://www.maxitoys.fr/marques/lego.html?limit=100',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        product_urls = hxs.select('//h2[@class="product-name"]//a/@href').extract()
        for url in product_urls:
            url = urljoin_rfc(base_url, url)
            yield Request(url, callback=self.parse_product)
        
        next_page = hxs.select('//div[@class="pages"]//li[@class="next"]//@href').extract()
        if next_page:
            url = urljoin_rfc(base_url, next_page[0])
            yield Request(url)
            
    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        
        loader = ProductLoader(item=Product(), response=response)
        identifier = hxs.select('//meta[@itemprop="productID"]/@content').re('sku: *(\d+)')

        name = u' '.join([x.strip() for x in hxs.select(u'//div[@class="product-name"]//text()').extract() if x.strip() != u''])

        sku = [x for x in name.split(' ') if x.isdigit() and len(x) > 2]
        sku = sku[0] if len(set(sku)) == 1 else ''

        category = hxs.select(u'//div[@class="breadcrumbs"]//li/a/text()').extract()
        category = category[-1].strip() if category else ''
        loader.add_value('identifier', identifier)
        loader.add_value('name', name)
        brand = hxs.select('//meta[@itemprop="brand"]/@content').extract()
        brand = brand[0].strip() if brand else ''
        loader.add_value('brand', brand)
        loader.add_value('category', category)
        loader.add_value('sku', sku)
        loader.add_value('identifier', identifier)
        loader.add_value('url', response.url)
        price =  hxs.select(u'//span[@class="price"]/text()').extract()
        price = extract_price_eu(price[0])
        #price = price[0].replace(',', '') if price else ''
        #if price:
            #price += hxs.select(u'//span[@class="price"]/sup/text()')[0].extract()
        loader.add_value('price', price)
        image = hxs.select(u'//div[contains(@class, "img-box")]//img/@src').extract()
        image = image[0] if image else ''
        loader.add_value('image_url', image)
        yield loader.load_item()
