import re
import json

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.utils import extract_price_eu

from product_spiders.items import (
    Product,
    ProductLoaderWithoutSpaces as ProductLoader
)

class KlimawebSpider(BaseSpider):
    name = 'klimaweb.it'
    allowed_domains = ['klimaweb.it']
    start_urls = ['http://www.klimaweb.it/index.php?route=information/sitemap']


    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = response.xpath('//li/a/@href').extract()

        for url in categories:
            yield Request(urljoin_rfc(base_url, url), self.parse_products)

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        next_pages = set(hxs.select('//div[@class="pagination"][1]/div[@class="links"]/a/@href').extract())

        for url in next_pages:
            yield Request(urljoin_rfc(base_url, url), self.parse_products)

        products = response.css('.product-grid .name').xpath('.//a/@href').extract()

        for url in products:
            yield Request(urljoin_rfc(base_url, url), self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('url', response.url)
        product_loader.add_xpath('name', '//h1//text()')
        product_loader.add_xpath('identifier', '//input[@name="product_id"]/@value')
        try:
            sku = hxs.select('//div[@class="description"]/span[contains(text(), '
                             '"Codice")]/following-sibling::text()').extract()[0].strip()
        except:
            sku = ''
        product_loader.add_xpath('sku', '//input[@name="product_id"]/@value')
        product_loader.add_xpath('image_url', '//img[@id="image"]/@src')
        brand = response.css('.description').xpath('.//a/span/text()').extract_first()
        product_loader.add_value('brand', brand)
        category = response.css('.breadcrumb').xpath('li[2]/a/span/text()').extract()
        product_loader.add_value('category', category)
        price = extract_price_eu(hxs.select('//div[@class="price"]/span/text()').extract()[0])
        product_loader.add_value('price', price)
        stock = ''.join(hxs.select('//div[@class="description"]/span/strong[contains(text(), '
                                   '"Disponibilit")]/../following-sibling::text()').extract()).strip().lower()
        if stock and not 'in magazzino' in stock:
            product_loader.add_value('stock', 0)

        yield product_loader.load_item()
