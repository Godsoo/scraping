import os
import json
import re
from copy import deepcopy

from scrapy import log

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.base_spiders.primary_spider import PrimarySpider

from utils import extract_price


from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class DolphinFitnessSpider(PrimarySpider):
    name = 'usn-dolphinfitness.co.uk'
    allowed_domains = ['dolphinfitness.co.uk']
    start_urls = ['http://www.dolphinfitness.co.uk']

    csv_file = 'dolphinfitness.co.uk_crawl.csv'

    def start_requests(self):
        brands = {'Sci-MX': ['http://www.dolphinfitness.co.uk/en/sci-mx'], 
                  'Optimum Nutrition': ['http://www.dolphinfitness.co.uk/en/optimum-nutrition'], 
                  'BSN': ['http://www.dolphinfitness.co.uk/en/bsn'], 
                  'PHD': ['http://www.dolphinfitness.co.uk/en/phd-nutrition', 'http://www.dolphinfitness.co.uk/en/phd-woman'],
                  'Maxi Nutrition': ['http://www.dolphinfitness.co.uk/en/maxinutrition'], 
                  'Reflex': ['http://www.dolphinfitness.co.uk/en/reflex'],
                  'Mutant': ['http://www.dolphinfitness.co.uk/en/mutant'],
                  'Cellucor': ['http://www.dolphinfitness.co.uk/en/cellucor'],
                  'USN': ['http://www.dolphinfitness.co.uk/en/usn']}
        for brand, brand_urls in brands.items():
            for brand_url in brand_urls:
                yield Request(brand_url, meta={'brand': brand})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        products = hxs.select('//div[@class="snapshot"]/div[@class="dsc"]/a/@href').extract()
        for product in products:
            yield Request(urljoin_rfc(get_base_url(response), product), callback=self.parse_product, meta=response.meta)

        next_page = []
        if next_page:
            next_page = urljoin_rfc(get_base_url(response), next_page[0])
            yield Request(next_page, callback=self.parse, meta=response.meta)


    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('name', '//div[@id="content"]/h1/text()')
        loader.add_value('url', response.url)
        loader.add_value('brand', response.meta.get('brand'))
        categories = [] #hxs.select('//div[@id="middle_col"]/a/text()').extract()[1:]
        for category in categories:
            loader.add_value('category', category)

        identifier = hxs.select('//div[@id="content"]//input[@type="hidden" and @name="v[order_id]"]/@value').extract()
        if not identifier:
            log.msg('PRODUCT WITHOUT IDENTIFIER: ' + response.url)
            return
 
        loader.add_value('identifier', identifier[0])
        loader.add_value('sku', identifier[0])

        image_url = hxs.select('//img[@id="prodphoto"]/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), image_url[0]))

        price = hxs.select('//div[@id="content"]//div[@id="price"]/div[@class="c2"]/text()').extract()
        loader.add_value('price', price)

        in_stock = hxs.select('//div[@id="content"]//div[@id="eta"]/div[@id="prodeta" and contains(text(),"In Stock")]')
        if not in_stock:
            loader.add_value('stock', 0)


        loader.add_value('shipping_cost', '0.00')

        item = loader.load_item()


        options = hxs.select('//div[@id="content"]//div[@class="prodoptions"]//input')
        if options:
            for option in options:
                option_item = deepcopy(item)
                option_item['identifier'] += '-' + option.select('./@value')[0].extract()
                option_item['name'] += ' ' + option.select('../text()')[0].extract()
                yield option_item
        else:
            yield item
