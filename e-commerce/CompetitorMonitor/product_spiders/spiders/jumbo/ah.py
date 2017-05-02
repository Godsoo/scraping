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
    name = 'ah.nl'

    data_filename = os.path.join(HERE, 'jumbodata.csv')
    start_urls = ('file://' + data_filename,)

    def parse(self, response):
        reader = csv.reader(StringIO(response.body))
        for row in reader:
            url = row[17]
            if url.startswith('http'):
                yield Request(url, meta={'sku': row[0]}, callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        link = hxs.select('//div[@class="detail"]/a/@href').extract()
        # Search result
        if link:
            yield Request(urljoin_rfc(base_url, link[0]), callback=self.parse_product, meta=response.meta)
            return

        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('identifier', '//a[@data-productid]/@data-productid')
        loader.add_value('sku', response.meta['sku'])
        loader.add_xpath('name', '//*[@itemprop="name"]/text()')
        loader.add_value('url', response.url)
        loader.add_xpath('price', '//*[@itemprop="price"]/@content')
        loader.add_xpath('image_url', '//*[@itemprop="image"]/@src')
        loader.add_xpath('brand', '//*[@itemprop="brand"]/@content')

        yield loader.load_item()
