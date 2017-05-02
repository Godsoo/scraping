from decimal import Decimal
from collections import OrderedDict

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
import re
import itertools

def get_shipping_cost(price):
    try:
        price = Decimal(price)
    except:
        price = Decimal('0.00')
    shipping_costs = OrderedDict([('16.99', '5.95'), ('24.99', '6.95'), ('39.99', '7.95'), ('59.99', '9.95'), ('99.99', '11.95'), ('174.99', '12.95'), ('10000000', '13.95')])
    for shipping_cost in shipping_costs.items():
        if price <= Decimal(shipping_cost[0]):
            return shipping_cost[1]
    if Decimal(price) > Decimal('175.00'):
        return '13.95'
    return ''

class ThewigcompanySpider(BaseSpider):
    name = 'thewigcompany.com'
    allowed_domains = ['thewigcompany.com']
    start_urls = ['http://thewigcompany.com/']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in hxs.select('//*[@id="nav-mega"]//li[contains(@class,"main")]/a/@href').extract():
            if url != '#':
                yield Request(urljoin_rfc(base_url, url + '?pgnum=1&pgsize=All'), callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        category = response.xpath('//*[@id="breadcrumbs"]/ul/li[2]/*/text()').extract_first()
        for url in response.xpath('//*[@id="grid-wrap"]//div[@class="grid-prod-name"]/a/@href').extract():
            yield Request(response.urljoin(url.strip()), callback=self.parse_product, meta={'category': category})

    @staticmethod
    def parse_product(response):
        hxs = HtmlXPathSelector(response)

        product_name = ''.join(hxs.select('//h1[@itemprop="name"]/text()').extract()).strip()
        sku = hxs.select('//span[@itemprop="productID"]/text()').extract()[0]
        img = hxs.select('//img[@class="default-image"]/@src').extract()
        category = response.meta.get('category')
        price = hxs.select('//*[@id="product-price"]//span[@itemprop="price"]/text()').extract()[0]
        price = extract_price(price)
        brand = hxs.select('//*[@id="product-right-col"]//span[@itemprop="brand"]/text()').extract()
        brand = brand[0] if brand else ''

        sizes = hxs.select('//*[@id="100000000045"]//input')
        colors = hxs.select('//*[@id="100000000046"]//input')

        if sizes or colors:
            size_variations = []
            for size in sizes:
                size_id = size.select('./@value').extract()[0]
                size_name = size.select('./following-sibling::label/span/text()').extract()[0]
                size_variations.append([size_id, size_name])
            color_variations = []
            for color in colors:
                color_id = color.select('./@value').extract()[0]
                color_name = color.select('./@onclick').extract()[0]
                color_name = re.findall("(?sim)'(.*?)'", color_name)
                color_variations.append([color_id, color_name[-1]])
            if sizes and colors:
                options = itertools.product(size_variations, color_variations)
            else:
                options = color_variations if colors else size_variations
            for option in options:
                product_identifier = sku
                name = product_name
                if sizes and colors:
                    for var in option:
                         product_identifier += '_'+ var[0]
                         name += ' ' + var[1]
                else:
                    product_identifier += '_'+ option[0]
                    name += ' ' + option[1]
                loader = ProductLoader(item=Product(), selector=hxs)
                loader.add_value('identifier', product_identifier)
                loader.add_value('sku', sku)
                loader.add_value('url', response.url)
                loader.add_value('name', name)
                loader.add_value('price', price)
                price = loader.get_output_value('price')
                loader.add_value('shipping_cost', get_shipping_cost(price))
                loader.add_value('brand', brand)
                if img:
                    loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))
                loader.add_value('category', category)
                yield loader.load_item()
        else:
            loader = ProductLoader(item=Product(), selector=hxs)
            loader.add_value('identifier', sku)
            loader.add_value('sku', sku)
            loader.add_value('url', response.url)
            loader.add_value('name', product_name)
            loader.add_value('price', price)
            price = loader.get_output_value('price')
            loader.add_value('shipping_cost', get_shipping_cost(price))
            loader.add_value('brand', brand)
            if img:
                loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))
            loader.add_value('category', category)
            yield loader.load_item()
