import re

# from scrapy.spider import BaseSpider
from scrapy.contrib.spiders import SitemapSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from productloader import load_product
from scrapy.http import FormRequest

from utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
import os
import csv

HERE = os.path.abspath(os.path.dirname(__file__))


class GetInTheMix(SitemapSpider):
    name = 'getinthemix.co.uk'
    allowed_domains = ['getinthemix.com']
    # start_urls = ('http://www.getinthemix.com',)
    sitemap_urls = [
        'http://www.getinthemix.com/sitemap.xml',
    ]
    sitemap_rules = [
        ('/', 'parse_product'),
    ]

    def __init__(self, *args, **kwargs):
        super(GetInTheMix, self).__init__(*args, **kwargs)

        self.product_skus = {}

        with open(os.path.join(HERE, 'getinthemix_skus.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.product_skus[row['name'].lower()] = row['sku']

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        product_name = hxs.select(u'//*[@class="listing-header-title"]/h1/text()').extract()

        if product_name:
            product_loader = ProductLoader(item=Product(), selector=hxs)
            product_loader.add_value('url', response.url)
            product_loader.add_value('name', product_name)
            try:
                product_loader.add_xpath('category', u'//div[@id="navtrail"]/a[2]/text()', lambda c: c[-1])
            except:
                pass
            product_loader.add_xpath('price', u'//div[@id="options_price"]/span[contains(@id, "options_pricevalue") and contains(@class, "price")]/text()')

            if product_name[0].lower() in self.product_skus:
                product_loader.add_value('sku', self.product_skus[product_name[0].lower()])
            product_loader.add_xpath('identifier', u'//input[@name="opt_1"]/@value')
            product_loader.add_xpath('image_url', '//img[@id="listing_main"]/@src')
            out_stock = hxs.select('//div[@id="options_stock"]/span[@class="listing_stock_out"]')
            if out_stock:
                product_loader.add_value('stock', 0)
            brand = hxs.select('//div[@class="listing-brand"]/a/img/@alt').extract()
            if not brand:
                for brand in hxs.select('//select[@id="q_brand"]/option/text()').extract():
                    if brand in product_name[0]:
                        break
                else:
                    brand = ''
            product_loader.add_value('brand', brand)
            item = product_loader.load_item()
            if item.get('identifier'):
                yield item

    '''
    def parse(self, response):
        # categories
        hxs = HtmlXPathSelector(response)
        category_urls = hxs.select('//ul[@id="nav"]//a/@href').extract()
        for url in category_urls:
            url = urljoin_rfc(response.url, url)
            yield Request(url)

        # subcategories
        subcategory_urls = hxs.select('//div[@class="cat_list"]//a/@href').extract()
        for url in subcategory_urls:
            url = urljoin_rfc(response.url, url)
            yield Request(url)

        # next page
        next_page = hxs.select('//span[@class="pager"]//li[@class="next"]/a/@href').extract()
        if next_page:
            url = urljoin_rfc(response.url, next_page[0])
            yield Request(url)

        for url in hxs.select('//li[@class="item"]/h2/a/@href').extract():
            url = urljoin_rfc(response.url, url)
            yield Request(url, callback=self.parse_product)
    '''
