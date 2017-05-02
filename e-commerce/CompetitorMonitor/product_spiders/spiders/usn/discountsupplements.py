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

class DiscountSupplementsSpider(PrimarySpider):
    name = 'usn-discount-supplements.co.uk'
    allowed_domains = ['discount-supplements.co.uk']
    start_urls = ['http://www.discount-supplements.co.uk']

    csv_file = 'discount-supplements.co.uk_crawl.csv'

    def start_requests(self):
        search_url = 'http://www.discount-supplements.co.uk/shopsearch.asp?fh_location=//root/en_GB/$s={}&fh_sort_by=price&fh_view_size=100'
        brands = ['Sci-MX', 'Optimum+Nutrition', 'BSN', 'PhD', 'Maxi Nutrition', 'Reflex', 'Mutant', 'Cellucor', 'USN']
        for brand in brands:
            yield Request(search_url.format(brand.replace(' ', '')), meta={'brand': brand.replace('+' , ' ')})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        products = hxs.select('//section[@id="content"]//a[@class="links"]/@href').extract()
        for product in products:
            yield Request(urljoin_rfc(get_base_url(response), product), callback=self.parse_product, meta=response.meta)

        next_page = hxs.select('//div[@class="page_holder"]/a[contains(text(),"next")]/@href').extract()
        if next_page:
            next_page = urljoin_rfc(get_base_url(response), next_page[0])
            yield Request(next_page, callback=self.parse, meta=response.meta)


    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)
        name = ' '.join(map(unicode.strip, hxs.select('//form[@name="frmProductLargeMain"]//span[@itemprop="name"]/text()')[:2].extract()))
        size = hxs.select('//span[@class="size"]/b/text()').extract()
        if size:
            name += ' ' + size[0]
        loader.add_value('name', name)
        loader.add_value('url', response.url)
        brand = response.meta.get('brand')
        loader.add_value('brand', brand)
        categories = hxs.select('//div[@id="middle_col"]/a/text()').extract()[1:]
        for category in categories:
            loader.add_value('category', category)

        identifier = hxs.select('//meta[@itemprop="productID"]/@content').extract()
        if not identifier:
            log.msg('PRODUCT WITHOUT IDENTIFIER: ' + response.url)
            return
 
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)

        image_url = hxs.select('//img[@itemprop="image"]/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), image_url[0]))

        price = hxs.select('//div[@class="price_holder"]/span[@class="price"]/text()').extract()
        loader.add_value('price', price)

        in_stock = hxs.select('//span[@class="price stockk"]/font[contains(text(),"In Stock")]')
        if not in_stock:
            loader.add_value('stock', 0)


        loader.add_value('shipping_cost', '0.00')

        item = loader.load_item()
        
        options = hxs.select('//form[@name="frmProductLargeMain"]//div[@class="leftcell"]/select[@name="catalogid" and @class="product_drop"][1]/option[@value!="-1"]')
        if options:
            for option in options:
                option_item = deepcopy(item)
                option_item['identifier'] += '-' + option.select('./@value')[0].extract()
                #option_item['sku'] += '-' + option.select('./@value')[0].extract()
                option_text = option.select('./text()')[0].extract()
                option_item['name'] += ' ' + option_text.split('-')[0].strip()
                if 'out of stock' in option_text.lower():
                    option_item['stock'] = 0
                yield option_item
        else:
            yield item
