import re
import json
from decimal import Decimal
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from product_spiders.items import Product, ProductLoader

from product_spiders.utils import extract_price_eu


class DominiDesign(BaseSpider):
    name = 'dominidesign.com'
    allowed_domains = ['dominidesign.com']
    start_urls = ['https://dominidesign.com/gb/']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for cat in hxs.select('//ul[@id="nav"]//a'):
            url = cat.select('@href').extract()[0]
            name = cat.select('string(span)').extract()[0]
            if name:
                yield Request(url, meta={'category': name}, callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select('//div[@class="category-products"]//h2[@class="product-name"]/a/@href').extract():
            yield Request(url, meta=response.meta, callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        image_url = hxs.select('//img[@itemprop="image"]/@src').extract()
        product_name = hxs.select('//div[@class="product-name"]/h1//text()').extract()[0]
        brand = hxs.select('//table[@id="product-attribute-specs-table"]//th[@class="label" and contains(text(), "Designer")]/following-sibling::td/text()').extract()
        price = hxs.select('//span[contains(@id, "price-including-tax-")]//text()').re(r'[\d,.]+')
        if not price:
            price = hxs.select('//meta[@itemprop="price"]/@content').extract()[0]
        try:
            product_identifier = hxs.select('//input[@name="product"]/@value').extract()[0].strip()
        except:
            product_identifier = hxs.select('//form[@id="product_addtocart_form"]/@action').re(r'/product/(\d+)')[0]

        options_config = re.search(r'var spConfig = new Product.Config\((.*)\)', response.body)
        if options_config:
            product_data = json.loads(options_config.groups()[0])
            products = {}
            for attr in product_data['attributes'].itervalues():
                for option in attr['options']:
                    for product in option['products']:
                        products[product] = ' - '.join((products.get(product, ''), option['label']))

            for identifier, option_name in products.iteritems():
                product_loader = ProductLoader(item=Product(), selector=hxs)
                sku = product_identifier + '_' + identifier
                product_loader.add_value('identifier', sku)
                product_loader.add_value('sku', sku)
                product_loader.add_value('name', product_name + option_name)
                if image_url:
                    product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
                if brand:
                    product_loader.add_value('brand', brand)
                price = float(product_data['basePrice']) * 1.2
                product_loader.add_value('price', round(price, 2))
                product_loader.add_value('url', response.url)
                product_loader.add_value('category', response.meta.get('category'))

                yield product_loader.load_item()
        else:
            product_loader = ProductLoader(item=Product(), selector=hxs)
            product_loader.add_value('identifier', product_identifier)
            product_loader.add_value('sku', product_identifier)
            product_loader.add_value('name', product_name)
            if image_url:
                product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            if brand:
                product_loader.add_value('brand', brand)
            product_loader.add_value('price', price)
            product_loader.add_value('url', response.url)
            product_loader.add_value('category', response.meta.get('category'))

            yield product_loader.load_item()
