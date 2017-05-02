import re
import csv
import json
from StringIO import StringIO

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from decimal import Decimal
from product_spiders.utils import extract_price

class RetroFurnishSkSpider(BaseSpider):

    name            = 'retrofurnish_sk'
    allowed_domains = ['retrofurnish.com/sk', 'retrofurnish.com']
    start_urls      = ('http://www.retrofurnish.com/en',)

    products_ids    = {}

    def parse(self, response):

        yield Request(
            url="http://www.retrofurnish.com/en",
            cookies={"currency:": "GBP"}, 
            callback=self.parse_real
        )

    def parse_real(self, response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//nav[@id="nav"]//a')
        for category in categories:
            url = category.select('./@href')[0].extract()
            category_name = category.select('./span/text()').extract()
            if not category_name:
                category_name = category.select('./text()').extract()
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_pagination, meta={'category': category_name})

    def parse_pagination(self, response):

        hxs = HtmlXPathSelector(response)
        base_url  = get_base_url(response)
        next_page = hxs.select('//div[@class="robot-link"]/a[contains(text(),"More products")]/@href').extract()

        if next_page:
            yield Request(next_page[0], callback=self.parse_pagination, meta=response.meta)

        products = hxs.select('//h2[@class="product-name"]/a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta=response.meta)


    def parse_product(self, response):

        hxs = HtmlXPathSelector(response)

        brand = hxs.select('//span[@class="title-designer-info"]/a/text()').extract()
        brand = brand[0] if brand else ''

        options = re.search('var spConfig = new Product.Config\((.*})\);', response.body)
        options = json.loads(options.group(1)) if options else None

        if options:
            product_name = options['productName']
            price        = options['basePrice']
            image_url    = options['imageUrl']
            identifier   = options['productId']
        else:
            product_name = hxs.select("//span[@class='h1']/text()")[0].extract()
            price        = hxs.select('//form//p[@class="special-price"]/span[@class="price"]/text()').extract()
            if not price:
                price = hxs.select('//form//span[@class="regular-price"]/span[@class="price"]/text()').extract()
#            price        = price[0].replace('.', '').replace(',', '.')
            image_url    = hxs.select("//div[@class='product-image-gallery']/img[contains(@id,'image')]/@src")[0].extract()
            identifier   = hxs.select('//input[@name="product"]/@value')[0].extract()

#        price = float(re.search('([\d\.]+)', price).group(1))
#        shipping = self.get_shipping_cost(price)

        product_loader = ProductLoader(item=Product(), selector=hxs)

        url = response.url
        product_loader.add_value('url', url)
        product_loader.add_value('name', product_name)
        product_loader.add_value('image_url', image_url)
        product_loader.add_value('brand', brand)
        product_loader.add_value('identifier', identifier)
        product_loader.add_value('category', response.meta.get('category') or '')
        product_loader.add_value('sku', identifier)
        product_loader.add_value('price', price)
#        product_loader.add_value('shipping_cost', shipping)

        if not options:
            product = product_loader.load_item()
            if product['identifier'] in self.products_ids:
                product['name'] = self.products_ids[product['identifier']]
            else:
                self.products_ids[product['identifier']] = product['name']
            yield product
            return

        option_names = {}
        for attr in options['attributes'].values():
            for opt in attr['options']:
                for prod in opt['products']:
                    option_names[prod] = option_names.get(prod, []) + [opt['label']]

        option_names = dict(map(lambda x: (x[0], ' '.join(x[1])), option_names.items()))
        for option in options.get('childProducts').iteritems():

            price = Decimal(option[1]['finalPrice']).quantize(Decimal('1.00'))
            shipping = self.get_shipping_cost(price)

            product_loader = ProductLoader(item=Product(), selector=hxs)
            product_loader.add_value('url', url)
            product_loader.add_value('name', '%s %s' % (product_name, option_names[option[0]]))
            product_loader.add_value('image_url', option[1]['imageUrl'])
            product_loader.add_value('identifier', option[0])
            product_loader.add_value('sku', identifier)
            product_loader.add_value('brand', brand)
            product_loader.add_value('category', response.meta.get('category') or '')
            product_loader.add_value('price', price)

            product = product_loader.load_item()

            if product['identifier'] in self.products_ids:
                product['name'] = self.products_ids[product['identifier']]
            else:
                self.products_ids[product['identifier']] = product['name']

            yield product


    def get_shipping_cost(self, price):
        if price >= 1000.0:
            return 200.0
        if price >= 700.0:
            return 140.0
        if price >= 500.0:
            return 90.0
        if price >= 300.0:
            return 50.0
        else:
            return 15.0
