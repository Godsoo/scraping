import os
import re
import json
import csv

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from decimal import Decimal

from product_spiders.items import Product, ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class LongMcQuadeSpider(BaseSpider):
    name = "hurricanegolf.com"
    allowed_domains = ["www.hurricanegolf.com", ]
    start_urls = [
        "http://www.hurricanegolf.com/",
        ]

    def __init__(self, *argv, **kwgs):
        super(LongMcQuadeSpider, self).__init__(*argv, **kwgs)

        self._ignore_urls = []
        self._ignore_names = []
        with open(os.path.join(HERE, 'ignore_urls.txt')) as f:
            for l in f:
                self._ignore_urls.append(l.strip())

        with open(os.path.join(HERE, 'remove.csv')) as f:
            reader = csv.reader(f)
            for row in reader:
                self._ignore_names.append(row[0])

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        # Dive in categories
        cats = hxs.select('//ol[@class="nav-primary"]/li//a/@href').extract()
        for cat in cats:
            yield Request(urljoin_rfc(base_url, cat), callback=self.parse_cat)

    def parse_cat(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        # Dive in next page, if it is
        pages = hxs.select('//div[@class="pages"][1]/ol/li/a/@href').extract()
        for url in pages:
            yield Request(url, callback=self.parse_cat)

        # Dive in product
        products = hxs.select('//h2[@class="product-name"]/a/@href').extract()
        for product in products:
            yield Request(product, callback=self.parse_product)

    def parse_product(self, response):
        if response.url in self._ignore_urls:
            return

        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        # Fill up the Product model fields
        # identifier =
        url = response.url
        name = hxs.select("//*[@class='product-name']/*[@itemprop='name']/text()").extract()
        price = hxs.select("//span[@itemprop='offers']/span[@itemprop='price']/@content").extract()
        # sku = hxs.select("//span[@id='ProductSKU']/text()").extract()
        # metadata =
        category = hxs.select("//li[contains(@class, 'category')]/a/text()").extract()
        image_url = hxs.select('//img[@id="image-main"]/@src').extract()
        # brand = hxs.select("//div[@class='SectionHeader']/h1/text()").extract()
        # shipping_cost =

        # l = ProductLoader(response=response, item=Product())
        # l.add_value('identifier', identifier)
        # l.add_value('url', url)

        # l.add_value('sku', sku)
        # l.add_value('metadata', metadata)
        # l.add_value('category', category)
        # l.add_value('image_url', image_url)
        # l.add_value('brand', brand)
        # l.add_value('shipping_cost', shipping_cost)

        free_shipping = hxs.select('//div[@class="product-img-box"]//div[@class="onsale-product-label-image"]/table/tr/td[text()[contains(.,"Shipping")] and text()[contains(.,"Free")]]').extract()
        if free_shipping:
            shipping_cost = Decimal(0)
            # l.add_value("shipping_cost", Decimal(0))
        else:
            shipping_cost = 11.99
            # l.add_value("shipping_cost", 11.99)

        identifier = hxs.select('//input[@name="product"]/@value').extract()
        if not identifier:
            self.log("ERROR identifier not found")
        else:
            identifier = identifier[0]
            # l.add_value("identifier",identifier[0])

        brand = hxs.select('//span[@itemprop="brand"]/@content').extract()
        if not brand:
            self.log("ERROR brand not found")
        else:
            brand = brand[0]
            # l.add_value("brand",brand[0])

        stock = 0
        try:
            p_stock = hxs.select('//meta[@itemprop="availability"]/@content').extract()[0].lower()
            if 'in_stock' in p_stock:
                stock = 1
        except:
            stock = None
            self.log("ERROR stock not found")

        options_config = re.search(r'var spConfig=new Product.Config\((.*)\)', response.body)
        if not options_config:
            options_config = re.search(r'var spConfig = new Product.Config\((.*)\)', response.body)

        if options_config:
            product_data = json.loads(options_config.groups()[0])
            products = {}
            prices = {}
            for attr in product_data['attributes'].itervalues():
                for option in attr['options']:
                    for product in option['products']:
                        products[product] = ' - '.join((products.get(product, ''), option['label']))
                        prices[product] = prices.get(product, 0) +  float(option['price'])

            for option_identifier, option_name in products.iteritems():
                l = ProductLoader(response=response, item=Product())
                l.add_value('name', name[0] + ' ' + option_name)
                #if (name[0] + ' ' + size.get('label')).strip() in self._ignore_names:
                #    continue
                l.add_value('price', float(price[0]) + prices[option_identifier])
                l.add_value("identifier", identifier + '-' + option_identifier)
                l.add_value("brand", brand)
                l.add_value("shipping_cost", shipping_cost)
                l.add_value('category', category)
                l.add_value('image_url', image_url)
                l.add_value('url', url)
                if stock is not None:
                    l.add_value("stock", stock)
                yield l.load_item()
        else:
            l = ProductLoader(response=response, item=Product())
            l.add_value('name', name)
            if name in self._ignore_names:
                return
            l.add_value('price', price)
            l.add_value("identifier", identifier)
            l.add_value("brand", brand)
            l.add_value("shipping_cost", shipping_cost)
            l.add_value('category', category)
            l.add_value('image_url', image_url)
            l.add_value('url', url)
            if stock is not None:
                l.add_value("stock", stock)
            yield l.load_item()
