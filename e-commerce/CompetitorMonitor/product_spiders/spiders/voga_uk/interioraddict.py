import re
import csv
from StringIO import StringIO
import json

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from scrapy import log

from phantomjs import PhantomJS

from datetime import datetime, timedelta


class InteriorAddictSpider(BaseSpider):
    name = 'voga_uk-interioraddict.com'
    allowed_domains = ['interioraddict.com']
    start_urls = ('http://www.interioraddict.com',)

    def __init__(self, *args, **kwargs):
        super(InteriorAddictSpider, self).__init__(*args, **kwargs)
        self.errors = []

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

        product_map_reg = re.search('productMap = (\{.*\});', response.body)
        product_config_reg = re.search('var spConfig = new Product.Config\((\{.*\})\);', response.body)

        if product_config_reg and product_map_reg:
            products = json.loads(product_config_reg.group(1))
            product_map = json.loads(product_map_reg.group(1))
            base_identifier = products[u'productId']
            product_name = products[u'productName']
            base_price = products[u'basePrice']

            collected_products = 0

            for identifier, product in products['childProducts'].items():
                product_details = product_map[identifier]
                delivery_estimate = self._get_delivery_estimate(product_details, response)
                product_loader = ProductLoader(item=Product(), response=response)
                if identifier:
                    product_loader.add_value('identifier', identifier)

                product_loader.add_value('price', product[u'finalPrice'])
                option_name = product_name
                for attr_id, attribute in products[u'attributes'].items():
                    for option in attribute['options']:
                        if identifier in option['products']:
                            option_name += ' ' + option['label']

                product_loader.add_value('name', option_name)
                product_loader.add_value('url', response.url)
                product_loader.add_value('category', category)
                product_loader.add_value('image_url', image_url)

                collected_products += 1

                item = product_loader.load_item()

                item['metadata'] = {'delivery_estimate': delivery_estimate}

                yield item

            if not collected_products:
                product_loader = ProductLoader(item=Product(), response=response)
                product_loader.add_value('name', product_name)
                product_loader.add_value('url', response.url)
                product_loader.add_value('category', category)
                product_loader.add_value('image_url', image_url)
                product_loader.add_value('price', base_price)
                product_loader.add_value('identifier', base_identifier)

                yield product_loader.load_item()

    def _get_delivery_estimate(self, product, response):
        in7days = datetime.now() + timedelta(days=7)
        due_in_date = datetime.strptime(product['due_in_date'], '%d/%m/%Y')
        if product['stock'] and product['stock'] > 0:
            if product['number_due_in'] and product['number_due_in'] > 0 and due_in_date > in7days:
                return product['due_in_date']
            return in7days.strftime('%d/%m/%Y')
        elif product['stock'] is not None and product['stock'] <= 0:
            if product['number_due_in'] and int(product['number_due_in']) > 0:
                return product['due_in_date']
            for i, l in enumerate(response.body.split('\n')):
                if "jQuery('#stock-status-tbl tbody').append(" in l:
                    delivery_estimate = response.body.split('\n')[i + 4].split('>')[1].split('<')[0]
            return delivery_estimate
        return ''
