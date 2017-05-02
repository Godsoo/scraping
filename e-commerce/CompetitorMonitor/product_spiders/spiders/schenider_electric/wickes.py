import os
import csv
from decimal import Decimal
from cStringIO import StringIO

from scrapy.spider import BaseSpider
from scrapy.http import Request

from product_spiders.items import Product, \
    ProductLoaderWithNameStrip as ProductLoader

from product_spiders.utils import extract_price

from schenideritems import ScheniderMeta

HERE = os.path.abspath(os.path.dirname(__file__))


class ScrewfixSpider(BaseSpider):
    name = 'schenider_electric-wickes.co.uk'
    allowed_domains = ['wickes.co.uk']

    filename = os.path.join(HERE, 'trial_skus.csv')
    start_urls = ('file://' + filename,)


    def parse(self, response):
        reader = csv.DictReader(StringIO(response.body))
        for row in reader:
            if 'http' in row['Wickes']:
                yield Request(row['Wickes'], callback=self.parse_product, meta={'row': row})

    def parse_product(self, response):
        
        row = response.meta['row']

        categories = response.xpath('//div[contains(@class, "breadcrumb")]//li/a[@class="bc__link bc__link--last"]/span/text()').extract()
        if categories:
            category = categories[0].strip()

        loader = ProductLoader(item=Product(), response=response)
        name = response.xpath('//h1/text()').extract()[0].strip()
        loader.add_value('name', name)
        identifier = response.xpath('//p[@class="productCode"]/text()').re('(\d+)')[0]
        loader.add_value('identifier', identifier)
        loader.add_value('sku', row['Reference'])
        image_url = response.xpath('//a/@data-img').re('src="(.*)\?\$')
        if image_url:
            loader.add_value('image_url', 'http:' + image_url[0])
        loader.add_value('url', response.url)
        price = response.xpath('//p[@class="price mainPrice"]/span/text()').extract()[0]
        price = round(extract_price(price) / Decimal(1.20), 2)
        loader.add_value('price', price)
        brand = response.xpath('//li[span[contains(text(), "Brand Name")]]/text()').extract()
        brand = brand[-1].strip() if brand else ''
        loader.add_value('brand', brand)
        categories = response.xpath('//div[@id="breadcrumb"]//li/a/span[@class="decoration"]/text()').extract()[2:-1]
        loader.add_value('category', categories)

        item = loader.load_item()

        metadata = ScheniderMeta()
        metadata['name'] = item['name']
        metadata['brand'] = item['brand']
        item['metadata'] = metadata

        yield item
