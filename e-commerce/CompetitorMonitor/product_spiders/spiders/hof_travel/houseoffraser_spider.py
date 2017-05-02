import re
import csv
import os
import shutil
from scrapy import signals
from scrapy import log
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from scrapy.xlib.pydispatch import dispatcher

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class HouseOfFraserSpider(BaseSpider):
    name = 'houseoffraser.co.uk-travel'
    allowed_domains = ['houseoffraser.co.uk']
    start_urls = ['http://www.houseoffraser.co.uk/Antler+Bags+Luggage/BRAND_ANTLER_17,default,sc.html&redirectQuery=antler?sz=200&spcl',
                  'http://www.houseoffraser.co.uk/Samsonite+Bags+Luggage/%20BRAND_SAMSONITE_17,default,sc.html&redirectQuery=samsonite?sz=200&spcl',
                  'http://www.houseoffraser.co.uk/Eastpak+Bags+Luggage/BRAND_EASTPAK_17,default,sc.html?sz=200&spcl',
                  'http://www.houseoffraser.co.uk/Wenger/BRAND_WENGER,default,sc.html?redirectQuery=wenger?sz=200&spcl']

    def __init__(self, *a, **kw):
        super(HouseOfFraserSpider, self).__init__(*a, **kw)
        dispatcher.connect(self.spider_closed, signals.spider_closed)

        reader = csv.DictReader(open(os.path.join(HERE, 'exclude_urls.csv')))
        self.exclude_urls = [row['url'] for row in reader]

    def spider_closed(self, spider):
        if spider.name == self.name:
            shutil.copy('data/%s_products.csv' % spider.crawl_id, os.path.join(HERE, 'houseoffraser_travel.csv'))
            log.msg("CSV is copied")

    def parse(self, response):
        if any(map(lambda url: response.url.startswith(url), self.exclude_urls)):
            return

        hxs = HtmlXPathSelector(response)
        category = hxs.select('//a[@itemprop="breadcrumb"]/text()').extract()[-1]
        products = hxs.select('//div[@class="mainColumn"]/ol[@class="productListing clearfix"]/li')
        if products:
            for product in products:
                loader = ProductLoader(item=Product(), selector=product)
                name = ' '.join(product.select('span[@class="productInfo"]/a/descendant::*/text()').extract())
                loader.add_value('name', name)
                loader.add_xpath('url', 'a/@href')
                loader.add_xpath('price', 'span/span[@class="price" or @class="priceNow"]/text()')
                url = loader.get_output_value('url')
                sku = self.extract_sku(url)
                image_url = product.select('a[@class="productImage"]/img[@class=" featuredProductImage"]/@src').extract()[0]
                loader.add_value('image_url', image_url)
                loader.add_value('sku', sku)
                loader.add_value('category', category)
                loader.add_xpath('brand', 'span[@class="productInfo"]/a/h3/text()')
                loader.add_value('identifier', sku)
                yield loader.load_item()
        next = hxs.select('//a[@class="pager nextPage"]/@href').extract()
        if next:
            yield Request(next[0], callback=self.parse_product)

    def extract_sku(self, url):
        r = re.search('ProductID=(\d+)', url)
        if r:
            sku = r.groups()[0]
        else:
            sku = url.split('/')[-1].split(',')[0]
        return sku
