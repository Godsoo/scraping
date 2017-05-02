import re
import csv
from StringIO import StringIO
import json

from decimal import Decimal

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from scrapy import log

from phantomjs import PhantomJS

from scrapy.item import Item, Field

class VogaMeta(Item):
    delivery_estimate = Field()

def delivery_estimate(p, m):
    from datetime import datetime
    if p['stock'] > 0:
        if datetime.strptime(p['due_in_date'], '%d/%m/%Y') < datetime.strptime(m, '%d/%m/%Y'):
            return m
        return p['due_in_date']
    else:
        if p['number_due_in'] > 0:
            return p['due_in_date']
        else:
            return '14-16 week delivery'

class InteriorAddictSpider(BaseSpider):
    name = 'voga_nw-interioraddict.com'
    allowed_domains = ['interioraddict.com']
    start_urls = ('http://www2.interioraddict.com/no/switcher/index/switch/?language=no&currency=NOK&destination=',)

    def parse(self, response):
        base_url = get_base_url(response)

        browser = PhantomJS()

        browser.get(response.url)

        hxs = HtmlXPathSelector(text=browser.driver.page_source)

        browser.close()

        categories = hxs.select('//div[@id="nav-full"]//a')
        for category in categories:
            url = category.select('./@href').extract()
            if url:
                meta = response.meta
                category_name = category.select('./span/text()').extract()
                meta['category'] = category_name[0] if category_name else ''
                yield Request(urljoin_rfc(base_url, url[0]), meta=meta, callback=self.parse_pagination)

    def parse_pagination(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        next_page = hxs.select('//a[contains(@class,"next") and @title="Next"]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]), meta=response.meta)

        products = hxs.select('//*[contains(@class, "product-name")]/a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        image_url = hxs.select('//img[@id="image"]/@src').extract()
        image_url = image_url[0] if image_url else ''
        try:
            category = hxs.select('//div[@class="breadcrumbs"]/ul//a/text()').extract()[-1]
        except:
            category = ''

        product_config_reg = re.search('var spConfig = new Product.Config\((\{.*\})\);', response.body)
        product_map_reg = re.search('var productMap = (\{.*\});', response.body)
        product_7_reg = re.search('in7Days =new Date\("(.*)"\);', response.body)

        if product_config_reg:
            products = json.loads(product_config_reg.group(1))
            base_identifier = products[u'productId']
            product_name = products[u'productName']
            base_price = products[u'basePrice']
            product_map = json.loads(product_map_reg.group(1))

            collected_products = 0

            for identifier, product in products['childProducts'].items():
                product_loader = ProductLoader(item=Product(), response=response)
                if identifier:
                    product_loader.add_value('identifier', identifier)

                product_loader.add_value('price', Decimal(product[u'finalPrice']).quantize(Decimal('1.00')))
                option_name = product_name
                for attr_id, attribute in products[u'attributes'].items():
                    for option in attribute['options']:
                        if identifier in option['products']:
                            option_name += ' ' + option['label']

                product_loader.add_value('name', option_name)
                product_loader.add_value('url', response.url)
                product_loader.add_value('category', category)
                product_loader.add_value('image_url', image_url)
                product_loader.add_value('stock', '1')

                collected_products += 1

                item = product_loader.load_item()
                meta = VogaMeta()
                meta['delivery_estimate'] = delivery_estimate(product_map[identifier], product_7_reg.group(1))
                item['metadata'] = meta
                yield item

            if not collected_products:
                product_loader = ProductLoader(item=Product(), response=response)
                product_loader.add_value('name', product_name)
                product_loader.add_value('url', response.url)
                product_loader.add_value('category', category)
                product_loader.add_value('image_url', image_url)
                product_loader.add_value('price', Decimal(base_price).quantize(Decimal('1.00')))
                product_loader.add_value('identifier', base_identifier)
                product_loader.add_value('stock', '1')

                item = product_loader.load_item()
                meta = VogaMeta()
                meta['delivery_estimate'] = delivery_estimate(product_map[base_identifier], product_7_reg.group(1))
                item['metadata'] = meta
                yield item
