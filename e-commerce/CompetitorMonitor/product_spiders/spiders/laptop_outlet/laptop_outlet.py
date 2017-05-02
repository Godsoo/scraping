import os
import csv
import shutil

from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from cStringIO import StringIO

from product_spiders.config import DATA_DIR

from laptopoutletitems import LaptopOutletMeta

HERE = os.path.abspath(os.path.dirname(__file__))


class LaptopOutletSpider(BaseSpider):
    name = 'laptop_outlet-laptopoutlet.co.uk'

    allowed_domains = ['laptopoutlet.co.uk']

    filename = os.path.join(HERE, 'laptop_outlet_products.csv')
    start_urls = ('file://' + filename,)

    def __init__(self, *args, **kwargs):
        super(LaptopOutletSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_closed, 'export_finished')

    def spider_closed(self, spider, reason):
        shutil.copy(os.path.join(DATA_DIR, '%s_products.csv' % spider.crawl_id), os.path.join(HERE, 'laptop_outlet_results.csv'))

    def parse(self, response):
        reader = csv.DictReader(StringIO(response.body))
        for row in reader:
            if row.get('URL', None):
                yield Request(row['URL'], callback=self.parse_product, meta={'row': row})

    def parse_product(self, response):

        row = response.meta['row']

        loader = ProductLoader(response=response, item=Product())
        loader.add_value('url', response.url)
        loader.add_value('identifier', row['Sku Number'].lower())
        loader.add_value('sku', row['Sku Number'])
        brand = response.xpath('//tr[th[contains(text(), "Brand")]]/td/text()').extract()
        brand = brand[0] if brand else ''
        loader.add_value('brand', brand)
        loader.add_value('category', row['Category'])
        loader.add_value('name', row['Title'])

        price = response.xpath(u'//div[@class="price-info"]//p[@class="special-price"]/span[@class="price"]/text()').extract()
        if not price:
            price = response.xpath(u'//div[@class="price-info"]//span[@class="regular-price"]/span[@class="price"]/text()').extract()

        loader.add_value('price', price[0])
        image_url = response.xpath('//img[@id="image-main"]/@src').extract()
        if image_url:
            loader.add_value('image_url', image_url[0])

        item = loader.load_item()

        metadata = LaptopOutletMeta()
        metadata['ean'] = row['EAN']
        item['metadata'] = metadata
        yield item

                
                
