import re
import csv
import os

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import (
    Product,
    ProductLoaderEU as ProductLoader
)

HERE = os.path.abspath(os.path.dirname(__file__))


class SaturnSpider(BaseSpider):
    name = 'logitech_german-saturn.de'
    allowed_domains = ['saturn.de']

    start_urls = ('http://www.saturn.de/webapp/wcs/stores/servlet/MultiChannelSearch?storeId=48352&langId=-3&searchProfile=onlineshop&searchParams=&path=&query=Logitech',)

    map_products_csv = os.path.join(HERE, 'logitech_map_products.csv')
    map_price_field = 'map'
    map_join_on = [('identifier', 'mpn'), ('identifier', 'ean13')]

    def start_requests(self):

        for url in self.start_urls:
            yield Request(url)

        with open(HERE + '/logitech_extra_products.csv') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['Saturn'] != 'No Match':
                    yield Request(row['Saturn'], callback=self.parse_product, meta={'sku':row['sku'], 'brand':row['brand']})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        next_page = hxs.select('//li[@class="pagination-next"]/a/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]))

        products = hxs.select('//div[@class="content "]/h2/a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        category = hxs.select('//ul[@class="breadcrumbs"]/li/a/text()').extract()

        stock = hxs.select('//div[contains(@class,"availability")]/ul/li/font/text()').extract()

        loader = ProductLoader(item=Product(), response=response)
        identifier = re.search('\'ean\',\'(.*?)\'', response.body).group(1)
        loader.add_value('identifier', identifier)

        sku = response.meta.get('sku', '')
        if sku:
            loader.add_value('sku', sku)
            loader.add_value('brand', response.meta.get('brand', ''))
        else:
            loader.add_value('sku', identifier)
            loader.add_value('brand', 'Logitech')

        loader.add_xpath('name', '//*[@itemprop="name"]/text()')
        loader.add_value('url', response.url)
        if category:
            loader.add_value('category', category[-1])
        price = hxs.select('//*[@itemprop="price"]/text()').extract()
        price = price[0] if price else 0
        loader.add_value('price', price)

        shipping_cost = hxs.select('//*[@itemprop="price"]/following-sibling::small/text()').re(u'\xa0(.*)')
        if shipping_cost:
            loader.add_value('shipping_cost', shipping_cost[0].strip().replace(',', '.'))
        if stock and 'liefertermin unbekannt' in stock[0].lower():
            loader.add_value('stock', 0)
        loader.add_xpath('image_url', '//*[@itemprop="image"]/@src', lambda imgs: map(lambda img: urljoin_rfc(base_url, img), imgs))

        yield loader.load_item()
