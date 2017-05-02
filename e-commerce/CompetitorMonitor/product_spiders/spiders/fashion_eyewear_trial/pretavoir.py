import os
import re
import csv
import json
from copy import deepcopy
from StringIO import StringIO

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from utils import extract_price

from scrapy.http import FormRequest
from product_spiders.items import ProductLoader, Product

HERE = os.path.abspath(os.path.dirname(__file__))

class pretavoirSpider(BaseSpider):

    name = "fashioneyewear-trial-pretavoir.co.uk"
    allowed_domains = ["www.pretavoir.co.uk"]

    filename = os.path.join(HERE, 'fashioneyeware_products.csv')
    start_urls = ('file://' + filename,)

    download_delay = 4

    def parse(self, response):
        rows = csv.DictReader(StringIO(response.body))
        for row in rows:
            url = row['Pret-A-Voir'].strip()
            if 'pretavoir' in url:
                yield Request(url, dont_filter=True, callback=self.parse_product, meta={'row':row})
             
    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        row = response.meta['row']

        name = hxs.select('//span[@itemprop="name"]/text()').extract()[0].strip()
        url = response.url
        price = hxs.select('//p[@class="special-price"]/span[@class="price"]/text()').extract()
        if not price:
            price = hxs.select('//span[@class="regular-price"]/span[@class="price"]/text()').extract()
        price = price[0] if price else 0

        l = ProductLoader(item=Product(), response=response)
        l.add_value('name', name)        
        l.add_value('url', response.url)
        l.add_value('sku', row['SKU'])
        l.add_value('price', price)
        identifier = hxs.select('//input[@name="productId"]/@value').extract()
        if not identifier:
            identifier = hxs.select('//input[@name="product"]/@value').extract()

        l.add_value('identifier', identifier)
        l.add_xpath('brand', '//tr[th/text()="Brand"]/td/text()')
        l.add_xpath('image_url', '//a[@id="shoe-spin"]/img/@src')
        categories = hxs.select('//li[@typeof="v:Breadcrumb"]/a/text()').extract()
        l.add_value('category', categories)
        in_stock = hxs.select('//div[@class="offer"]//p[@class="availability in-stock"]')
        if not in_stock:
            l.add_value('stock', 0)
        item = l.load_item()

        options_config = re.search(r'var spConfig = new Product.Config\((.*)\)', response.body)
        if options_config:
            option_item = deepcopy(item)
            product_data = json.loads(options_config.groups()[0])
            products = {}
            prices = {}
            for attr in product_data['attributes'].itervalues():
                for option in attr['options']:
                    for product in option['products']:
                        products[product] = ' - '.join((products.get(product, ''), option['label']))
                        prices[product] = prices.get(product, 0) +  extract_price(option['price'])

            for option_id, option_name in products.iteritems():
                option_item = deepcopy(item)
                option_item['identifier'] = option_item['identifier'] + '-' + option_id
                option_item['name'] = option_item['name'] + re.findall('(.*) \(', option_name)[0]
                option_item['price'] = option_item['price'] + prices[option_id]
                if 'IN STOCK' not in option_name.upper():
                    option_item['stock'] = 0
                yield option_item
        else:
            yield item
