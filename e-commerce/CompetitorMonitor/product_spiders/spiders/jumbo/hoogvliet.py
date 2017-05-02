import os
import csv
from scrapy.spider import BaseSpider
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from cStringIO import StringIO
from scrapy.selector import HtmlXPathSelector
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

HERE = os.path.abspath(os.path.dirname(__file__))


class AHSpider(BaseSpider):
    name = 'hoogvliet.com'

    data_filename = os.path.join(HERE, 'jumbodata.csv')
    start_urls = ('file://' + data_filename,)

    def parse(self, response):
        reader = csv.reader(StringIO(response.body))
        for row in reader:
            url = row[21]
            if url.startswith('http'):
                yield Request(url, meta={'sku': row[0]}, callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        try:
            product_name = hxs.select('//*[@itemprop="name"]/text()').extract()[-1]
        except:
            link = hxs.select('//div[@class="ws-product-title"]/a/@href').extract()
            yield Request(link[0], callback=self.parse_product, meta=response.meta)
            return

        try:
            product_brand = hxs.select('//*[@itemprop="brand"]//text()').extract()[-1]
        except:
            product_brand = ''

        image_url = hxs.select('//*[@itemprop="image"]/@src').extract()
        if image_url:
            image_url = urljoin_rfc(base_url, image_url[0])

        product_price = ''.join(hxs.select('//*[@itemprop="price"]//text()').re(r'[\d.,]+'))

        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('identifier', '//input[@name="ProductSKU"]/@value')
        loader.add_value('sku', response.meta['sku'])
        loader.add_value('name', product_name)
        loader.add_value('url', response.url)
        loader.add_value('price', product_price)
        loader.add_value('image_url', image_url)
        loader.add_value('brand', product_brand)

        item = loader.load_item()

        if item['identifier'].strip():
            yield loader.load_item()
