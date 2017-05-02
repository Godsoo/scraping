import os
import shutil

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class CoverBrandsSpider(BaseSpider):
    name = 'coverbrands.no'
    allowed_domains = ['coverbrands.no']
    start_urls = ['http://www.coverbrands.no/']

    user_agent = 'Googlebot/2.1 (+http://www.google.com/bot.html)'

    def __init__(self, *args, **kwargs):
        super(CoverBrandsSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_closed, signals.spider_closed)

    def spider_closed(self, spider):
        if spider.name == self.name:
            shutil.copy('data/%s_products.csv' % spider.crawl_id, os.path.join(os.path.dirname(HERE),
                        'cocopanda/coverbrands.csv'))
            self.log('CSV is copied')

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//ul[@id="nav"]/li/a/@href').extract()
        for url in categories:
            if 'limit=all' not in url:
                url = url + '?limit=all' if not '?' in url else url + '&limit=all'
            yield Request(url, callback=self.parse_product_list)

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)
        meta = {'category': hxs.select('//ul[@id="nav"]/li[contains(@class, "active")]/a/span/text()').extract()[0].strip()}
        urls = hxs.select('//ul/li[contains(@class, "item")]//h2[@class="fp-article-title"]/a/@href').extract()
        for url in urls:
            yield Request(url, self.parse_product, meta=meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        product_loader = ProductLoader(item=Product(), selector=hxs)
        brand = hxs.select('//div[@class="product-shop"]//h1[@itemprop="name"]/span/text()').extract()
        if brand:
            product_loader.add_value('brand', brand[0].strip())
        identifier = hxs.select('//div[@class="no-display"]/input[@name="product"]/@value').extract()[0].strip()
        product_loader.add_value('identifier', identifier + '.0')  # This is done to avoid fixing the identifiers in the database
        product_loader.add_value('sku', identifier)
        product_loader.add_xpath('name', '//div[@class="product-shop"]//h1[@itemprop="name"]/text()')
        price = ''.join(hxs.select('//span[@id="product-price-%s"]/text()' % identifier).extract()[0].strip().replace(',', '.').split())
        if not price:
            price = ''.join(hxs.select('//span[@id="product-price-%s"]/span/text()' % identifier).extract()[0].strip().replace(',', '.').split())
        if not price:
            self.log('WARNING: NON PRICE!')
        product_loader.add_value('price', price)
        product_loader.add_value('category', response.meta['category'])
        product_loader.add_xpath('image_url', '//a[@id="image-zoom"]/img/@src')
        product_loader.add_value('url', response.url)

        yield product_loader.load_item()
