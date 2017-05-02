from scrapy.selector import HtmlXPathSelector
from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin as urljoin_rfc
import itertools
from product_spiders.utils import extract_price
import re
import json

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class CBBedsonlegsCoUkSpider(BaseSpider):
    name = 'colourbank-bedsonlegs.co.uk'
    allowed_domains = ['bedsonlegs.co.uk']
    start_urls = ['http://www.bedsonlegs.co.uk/index.html']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        categories = hxs.select('//ul[@id="nav"]//li/a/@href').extract()
        categories += hxs.select('//li[@class="range"]/a/@href').extract()
        categories += hxs.select('//ul[contains(@class, "medium-block-grid") and not(contains(@class, "products-grid"))]//a/@href').extract()

        for url in categories:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url)

        for url in hxs.select('//ul[contains(@class, "products-grid")]//li/a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product)

        next = hxs.select('//a[@class="next i-next"]/@href').extract()
        if next:
            yield Request(urljoin_rfc(get_base_url(response), next[0]))

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_identifier = hxs.select('.//input[@name="product"]/@value').extract()[0]
        product_loader.add_value('identifier', product_identifier)
        product_loader.add_value('url', response.url)

        name = hxs.select('//div[@class="product-name"]/h1/text()').extract()[0]
        product_loader.add_value('name', name)
        category = hxs.select('//ul[@class="breadcrumbs"]/li/a/text()').extract()[1:-1]
        product_loader.add_value('category', category)
        product_loader.add_value('sku', product_identifier)
        img = hxs.select('//img[@id="main-img"]/@src').extract()
        if img:
            product_loader.add_value('image_url', urljoin_rfc(get_base_url(response), img.pop()))

        price = hxs.select('//form//p[@class="special-price"]/span[@class="price"]/text()').extract()
        if not price:
            price = hxs.select('//form//span[@class="regular-price"]/span[@class="price"]/text()').extract()
        price = extract_price(price[0]) if price else 0
        product_loader.add_value('price', price)

        item = product_loader.load_item()


        options_config = re.search(r'var spConfig = new Product.Config\((.*)\)', response.body)
        if options_config:
            product_data = json.loads(options_config.groups()[0])
            products = {}
            prices = {}
            for attr in product_data['attributes'].itervalues():
                for option in attr['options']:
                    for product in option['products']:
                        products[product] = ' - '.join((products.get(product, ''), option['label']))
                        prices[product] = prices.get(product, 0) + extract_price(option['price'])

            for identifier, option_name in products.iteritems():
                product_loader = ProductLoader(item=Product(), selector=hxs)
                product_loader.add_value('identifier', item['identifier'] + '_' + identifier)
                product_loader.add_value('sku', item['identifier'] + '_' + identifier)
                product_loader.add_value('name', item['name'] + ' ' + option_name)
                product_loader.add_value('image_url', item['image_url'])
                price = item['price'] + prices[identifier]
                product_loader.add_value('price', price)
                product_loader.add_value('url', response.url)
                product_loader.add_value('brand', '')
                product_loader.add_value('category', category)
                option_item = product_loader.load_item()
                yield option_item

        else:
            yield item
