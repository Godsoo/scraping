import json

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader,
)

from scrapy.http import Request
from decimal import Decimal
from copy import deepcopy
from product_spiders.utils import extract_price


class DerbyhouseSpider(BaseSpider):

    name = "derbyhouse"
    allowed_domains = ["derbyhouse.co.uk"]
    start_urls = ["http://www.derbyhouse.co.uk/"]
    base_url = "http://www.derbyhouse.co.uk"

    collected_names = {}

    rotate_agent = True
    cookies_enabled = 0

    def start_requests(self):
        for url in self.start_urls:
            yield Request(url)

    def parse(self, response):

        hxs = HtmlXPathSelector(response=response)
        categories = hxs.select('//li[contains(@class, "level2 nav")]/a')
        self.log('Found %d categories' %len(categories))
        for category in categories:
            url = category.select('./@href').extract()[0]
            name = category.select('text()').extract()[0]
            yield Request(url, meta={'category':name},
                          callback=self.parse_category)


    def parse_top_category(self, response):

        hxs = HtmlXPathSelector(response=response)
        categories = hxs.select("//ol[@id='Hierarchy1']/li/a")

        for category in categories:

            link = self.base_url + category.select("./@href").extract()[0]

            yield Request(url=link, callback=self.parse_category)

    def parse_category(self, response):

        hxs = HtmlXPathSelector(response=response)
        brands = hxs.select('//dt[contains(@data-id, "manufacturer_filter")]/following-sibling::dd[1]/ol/li/a')
        for brand in brands:
            url = brand.select('@href').extract()[0]
            name = brand.select('@title').extract()[0]
            yield Request(url=url, meta={'brand': name, 'category':response.meta['category']}, callback=self.parse_brand)

    def parse_brand(self, response):
        hxs = HtmlXPathSelector(response=response)
        products = hxs.select("//ul[contains(@class, 'products-grid')]/li//h2[@class='product-name']")

        for product in products:

            name = product.select("./a/text()").extract()[0]
            url = product.select("./a/@href").extract()[0]

            yield Request(url=url, meta={'name': name,
                                         'brand':response.meta['brand'],
                                         'category':response.meta['category']},
                          callback=self.parse_product)


        try:
            next_page = hxs.select("//a[contains(@class, 'next')]/@href").extract()[0]
            yield Request(next_page, callback=self.parse_brand, meta={'brand': response.meta['brand'], 'category': response.meta['category']})
        except:
            pass



    def parse_product(self, response):

        hxs = HtmlXPathSelector(response)
        name = response.meta['name'] if 'name' in response.meta else response.meta['_product']['name']
        url = response.url

        stock = 0 if 'out of stock' in response.body.lower() else 1
        sku = hxs.select('//button/@data-id').extract()
        if sku:
            sku = sku[0]
        else:
            sku = hxs.select('//div[@class="sku"]/text()').re('Code: *(.+)')[0]
        identifier = hxs.select('//input[@name="product"]/@value').extract()[0]
        price = hxs.select("//span[@id='product-price-%s']//text()" %identifier).extract()

        brand = response.meta['brand']
        category = response.meta['category']

        image_url = hxs.select('//div[@class="product-img-box"]//img/@pagespeed_lazy_src').extract()
        if not image_url:
            image_url = hxs.select('//div[@class="product-img-box"]//img/@src').extract()
        if not image_url:
            image_url = hxs.select('//img[@id="image-main"]/@src').extract()
        image_url = image_url[0] if image_url else ''

        options_config = hxs.select('//script/text()').re('Product.Config\((.*)\)')

        if options_config:
            product_data = json.loads(options_config[0])
            products = {}
            prices = {}
            options_ids = {}
            for attr in product_data['attributes'].itervalues():
                for option in attr['options']:
                    for product in option['products']:
                        products[product] = ' '.join((products.get(product, ''), option['label']))
                        prices[product] = prices.get(product, 0) + extract_price(option['price'])
                        options_ids[product] = option['id']

        if options_config:
            for option_identifier, option_name in products.iteritems():
                l = ProductLoader(item=Product(), response=response)

                l.add_value('image_url', image_url)
                l.add_value('url', url)
                l.add_value('stock', stock)
                l.add_value('brand', brand)
                l.add_value('identifier', option_identifier)
                l.add_value('sku', sku)
                l.add_value('name', name + option_name)
                l.add_value('price', extract_price(product_data['basePrice']) + prices[option_identifier])
                l.add_value('category', category)
                item = l.load_item()
                if item['identifier'] in self.collected_names:
                    # Filter duplicates, takes lowest price
                    # Check DuplicateProductPickerPipeline for more info
                    item['name'] = self.collected_names[item['identifier']]
                else:
                    self.collected_names[item['identifier']] = item['name']

                yield item

        else:
            l = ProductLoader(item=Product(), response=response)

            l.add_value('image_url', image_url)
            l.add_value('url', url)
            l.add_value('stock', stock)
            l.add_value('brand', brand)
            l.add_value('identifier', identifier)
            l.add_value('sku', sku)
            l.add_value('name', name)
            l.add_value('price', price)
            l.add_value('category', category)
            item = l.load_item()
            if item['identifier'] in self.collected_names:
                # Filter duplicates, takes lowest price
                # Check DuplicateProductPickerPipeline for more info
                item['name'] = self.collected_names[item['identifier']]
            else:
                self.collected_names[item['identifier']] = item['name']

            yield item


    def parse_option(self, options, ids, item):

        option = options.popitem()[1]['options']
        for variant in option:
            item['name'] += ' - ' + variant['label']
            item['price'] += Decimal(variant['price'])
            if ids:
                ids = set(ids) & set(variant['products'])
            else:
                ids = set(variant['products'])

            if len(ids) == 1:
                item['identifier'] = ids.pop()
                if item['identifier'] in self.collected_names:
                    item['name'] = self.collected_names[item['identifier']]
                else:
                    self.collected_names[item['identifier']] = item['name']
                yield item
                return
            else:
                for i in self.parse_option(deepcopy(options), ids, deepcopy(item)):
                    yield i


    def closing_parse_simple(self, response):
        """
        Overwrite BSM spider method to filter duplicates
        """
        for item in super(DerbyhouseSpider, self).closing_parse_simple(response):
            if item['identifier'] in self.collected_names:
                # Filter duplicates, takes lowest price
                # Check DuplicateProductPickerPipeline for more info
                item['name'] = self.collected_names[item['identifier']]
            else:
                self.collected_names[item['identifier']] = item['name']

            yield item
