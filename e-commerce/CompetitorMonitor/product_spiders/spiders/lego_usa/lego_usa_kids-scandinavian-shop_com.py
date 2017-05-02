import csv
import os
import copy
import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter
from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class ScandinavianShopSpider(BaseSpider):
    name = 'lego_usa_kids-scandinavian-shop_com'
    allowed_domains = ['kids-scandinavian-shop.com']
    start_urls = ['https://kids-scandinavian-shop.com/lego-toys-c-18/']

    # Map deviation screenshot feature
    map_deviation_detection = True
    map_deviation_csv = os.path.join(HERE, 'kids-scandinavian-shop_map_deviation.csv')

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        for url in hxs.select('//div[@class="catbox"]/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url))

        next = hxs.select('//a[contains(@title, "Next Page")]/@href').extract()
        if next:
            yield Request(urljoin_rfc(base_url, next[0]))

        products = hxs.select('//div[@class="prodinfo"]/a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        product_url = response.url.split('?')[0]

        loader = ProductLoader(item=Product(), response=response)
        identifier = re.search(r'p-(\d+).html$', product_url).group(1)
        loader.add_value('identifier', identifier)
        loader.add_xpath('name', '//h1[@id="productName"]/text()')
        loader.add_value('brand', 'LEGO')
        loader.add_value('category', hxs.select('//div[@id="navBreadCrumb"]/a/text()').extract()[-1])
        loader.add_xpath('sku', '//ul[attribute::id="pd-dtls-nfo"]/li[1]/text()', re=r'(\d+)')
        loader.add_value('url', product_url)
        loader.add_xpath('price', '//div[attribute::id="pd-dtls"]/span[1]', re=r'[\d.,]+')
        image_url = hxs.select('//div[attribute::id="pd-imgs"]/a[1]/img[1]/@src').extract()
        if image_url:
            image_url = urljoin_rfc(base_url, image_url[0])
        loader.add_value('image_url', image_url)

        yield loader.load_item()
