import re
import os
import json
import csv

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter

from product_spiders.items import Product
from axemusic_item import ProductLoader as AxeMusicProductLoader

from scrapy.spider import BaseSpider

from lxml.etree import XMLSyntaxError

HERE = os.path.abspath(os.path.dirname(__file__))


class TomLeeMusicCaSpider(BaseSpider):
    name = 'tomleemusic.ca'
    allowed_domains = ['tomleemusic.ca', 'competitormonitor.com']
    start_urls = ['http://www.tomleemusic.ca']

    download_timeout = 1800

    product_loader = AxeMusicProductLoader

    def __init__(self, *args, **kwargs):
        super(TomLeeMusicCaSpider, self).__init__(*args, **kwargs)
        self._brands = []
        with open(os.path.join(HERE, 'tomleemusic_brands.json')) as f:
            self._brands = json.load(f)
            self._brands.sort(key=lambda b: len(b), reverse=True)

    def _get_brand_from_name(self, name):
        for brand in self._brands:
            if name.startswith(brand):
                return brand
        return ''

    def start_requests(self):
        yield Request('http://www.tomleemusic.ca/index.php/catalogsearch/result/index/?limit=all&q=%25',
                      callback=self.parse,
                      dont_filter=True)
        yield Request('http://www.tomleemusic.ca/index.php/shopping/', callback=self.parse)

        prev_crawl_file = self._get_prev_crawl_file()
        if os.path.exists(prev_crawl_file):
            with open(prev_crawl_file) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['url']:
                        yield Request(row['url'], callback=self.parse_product)

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return

        hxs = HtmlXPathSelector(response)
        try:
            for url in hxs.select('//li[contains(@class, "nav-item level0 nav-3")]/div//a/@href').extract():
                url = urljoin_rfc(get_base_url(response), url)
                yield Request(url, callback=self.parse)

            for url in hxs.select('//ul[contains(@class, "accordion")]/li/a/@href').extract():
                url = urljoin_rfc(get_base_url(response), url)
                yield Request(url, callback=self.parse)

            items = hxs.select('//h2[@class="product-name"]/a/@href').extract()
            for url in items:
                url = urljoin_rfc(get_base_url(response), url)
                yield Request(url, callback=self.parse_product)

            next = hxs.select('//li[@class="next"]/a/@href').extract()
            if next:
                yield Request(urljoin_rfc(get_base_url(response), next[-1]), callback=self.parse)

        except XMLSyntaxError:
            return

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        product_loader = AxeMusicProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('url', response.url)
        product_loader.add_xpath('name', u'//div[@class="product-name"]/h1/text()')
        price = hxs.select(u'//div[@class="price-box"]//span[@class="price"]/text()').extract()
        if price:
            price = price[0].strip()
            product_loader.add_value('price', price)
        else:
            return
        product_loader.add_xpath('sku', u'//div[@class="sku"]/span[@class="value"]/text()')
        product_loader.add_xpath('category', u'//div[@class="breadcrumbs"]/ul/li[2]/a/span/text()')

        img = hxs.select('//img[@id="image-main"]/@src').extract()
        if img:
            img = urljoin_rfc(get_base_url(response), img[0])
            product_loader.add_value('image_url', img)

        identifier = hxs.select('//meta[@itemprop="productID"]/@content').re('sku:(.*)')[0]
        product_loader.add_value('identifier', identifier)

        product_loader.add_value('brand', self._get_brand_from_name(product_loader.get_output_value('name')))

        #stock_status = ''.join(hxs.select('//p[@class="availability in-stock"]/h10/text()').extract()).strip()
        # if stock_status:
        #     if 'OUT OF STOCK' in stock_status.upper():
        #         product_loader.add_value('stock', 0)

        yield product_loader.load_item()
