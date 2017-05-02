import re
import json
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price

from copy import deepcopy


class DesignACakeSpider(BaseSpider):
    name = 'designacake'
    allowed_domains = ['design-a-cake.co.uk']
    start_urls = (
        'http://www.design-a-cake.co.uk/',
    )

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # parse categories
        urls = hxs.select('//*[@id="nav"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list)

    def parse_products_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        category = hxs.select('//div[contains(@class, "page-title") and contains(@class, "category-title")]/h1/text()').extract()

        urls = hxs.select('//h2[@class="product-name"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta={'category': category})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_name = hxs.select('//div[@class="product-name"]/h1/text()').extract()[0]
        image_url = hxs.select('//*[@id="image-zoom"]/img/@src').extract()
        if image_url:
            product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        product_loader.add_value('name', product_name)
        product_loader.add_value('url', response.url)
        sku = hxs.select('//div[contains(@class, "product-sku")]/span[@class="value"]/text()').extract()[0]
        product_loader.add_value('identifier', sku)
        product_loader.add_value('sku', sku)
        price = hxs.select('//span[@class="price-including-tax"]/span[@class="priinc"]/text()').extract()[0]
        product_loader.add_value('price', extract_price(price))
        in_stock = hxs.select('//p[contains(@class, "availability") and contains(@class, "in-stock")]')
        if not in_stock:
            product_loader.add_value('stock', 0)
        category = response.meta.get('category')
        if category:
            product_loader.add_value('category', category)
        product = product_loader.load_item()

        options_config = re.search(r'var spConfig = new Product.Config\((.*)\)', response.body)
        if options_config:
            product_data = json.loads(options_config.groups()[0])
            products = {}
            for attr in product_data['attributes'].itervalues():
                for option in attr['options']:
                    for product_id in option['products']:
                        products[product_id] = ' - '.join((products.get(product_id, ''), option['label']))
            for identifier, option_name in products.iteritems():
                product_option = deepcopy(product)
                product_option['name'] = product_data['childProducts'][identifier]['productName']
                product_option['sku'] = product_data['childProducts'][identifier]['sku']
                product_option['price'] = product_data['childProducts'][identifier]['price']
                product_option['identifier'] = product_data['childProducts'][identifier]['sku']
                yield product_option
        else:
            yield product
