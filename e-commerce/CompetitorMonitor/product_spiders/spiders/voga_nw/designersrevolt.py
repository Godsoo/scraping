import re
import csv
from StringIO import StringIO

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url


class DesignersRevoltSpider(BaseSpider):
    name = 'voga_nw-designersrevolt.com'
    allowed_domains = ['designersrevolt.com']
    start_urls = ('http://www.designersrevolt.com/en/all_categories.php',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//a[contains(@href,"category")]')
        for category in categories:
            url = category.select('./@href')[0].extract()
            category_name = category.select('./text()')[0].extract()
            yield Request(urljoin_rfc(base_url, url), meta={'category': category_name})

        products = hxs.select('//a[contains(@class,"prodname")]/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product_options, meta=response.meta)

    def parse_product_options(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        options = hxs.select('//div[contains(@class,"optionable")]/a[@class="select"]/@href').extract()
        for url in options:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta=response.meta)

        for product in self.parse_product(response):
            yield product

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('url', response.url)
        name = hxs.select('//span[@class="crumbactive"]/text()')[0].extract().strip()
        option_name = hxs.select('//div[@id="selectionpanel"]/span[@class="selection left tipme"]/text()').extract()
        option_name = option_name[0].strip() if option_name else ''
        product_loader.add_value('name', '%s %s' % (name, option_name))
        image_url = hxs.select('//li[@id="prime_0"]/a[img]/@href').extract()
        if image_url:
            image_url = urljoin_rfc(base_url, image_url[0])
            product_loader.add_value('image_url', image_url)
        identifier = hxs.select('//div[@id="selectionpanel"]/span[@class="selection left tipme"]/@title')[0].extract()
        product_loader.add_value('identifier', identifier)
        product_loader.add_value('sku', identifier)
        price = hxs.select('//span[@class="cost"]/text()')[0].extract().replace(',', '')
        product_loader.add_value('price', price)
        product_loader.add_value('category', response.meta.get('category'))
        product_loader.add_value('shipping_cost', '49.00' if float(product_loader.get_output_value('price')) < 500.00 else '0.00')
        stock = hxs.select('//span[@class="instockinfo"]/text()').extract()
        if stock:
            if 'In Stock' not in stock[0]:
                product_loader.add_value('stock', 0)
        yield product_loader.load_item()
