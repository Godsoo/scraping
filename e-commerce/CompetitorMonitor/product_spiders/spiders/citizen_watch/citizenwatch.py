import os
import csv
from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class CItizenWatchSpider(BaseSpider):
    name = 'citizenwatch.com'
    allowed_domains = ['citizenwatch.com']
    start_urls = ('http://www.citizenwatch.com/en-uk/',)

    def parse(self, response):
        with open(os.path.join(HERE, 'citizenproducts.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                yield Request('http://www.citizenwatch.com/en-uk?s=%s' % row['SKU'],
                              callback=self.parse_product,
                              meta={'row': row})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        row = response.meta['row']

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('sku', row['SKU'])
        loader.add_value('price', row['RRP'])
        loader.add_value('identifier', row['SKU'])
        loader.add_xpath('image_url', '//div[@id="watchListing"]/div/div[@class="watch_img"]/input[@class="img_src"]/@value')
        loader.add_xpath('url', '//div[@id="watchListing"]/div/a[@class="full_link"]/@href')
        loader.add_xpath('name', '//div[@id="watchListing"]/div/div[@class="content"]/h3/text()')

        item = loader.load_item()

        if not item.get('name') and not response.meta.get('retry_us', False):
            yield Request('http://www.citizenwatch.com/en-us?s=%s' % row['SKU'],
                          callback=self.parse_product,
                          meta={'row': row,
                                'retry_us': True},
                          dont_filter=True)
            return
        elif not item.get('name'):
            item['name'] = row['NAME']

        yield item
