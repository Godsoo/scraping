import csv
import os

from scrapy import log
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import (Product,
        ProductLoaderWithNameStrip as ProductLoader)
from product_spiders.fuzzywuzzy import process, fuzz

HERE = os.path.abspath(os.path.dirname(__file__))


class SwellukSpider(BaseSpider):
    name = 'swelluk.com'
    allowed_domains = ['swelluk.com']
    start_urls = ['http://www.swelluk.com']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        cats = hxs.select("//nav/ul/li/a[contains(@href, 'http')]/@href").extract()
        if cats:
            for cat in cats:
                yield Request(
                        url=cat,
                        callback=self.parse_subcat)

    def parse_subcat(self, response):
        hxs = HtmlXPathSelector(response)
        subcats = hxs.select("//nav/div/ol//li/ul/li/a/@href").extract()
        if subcats:
            for subcat in subcats:
                yield Request(
                        url=subcat,
                        callback=self.parse_products,
                        meta={'do_pagination': True})

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        div = hxs.select('//ul[@id="prod_page"]')
        if div:
            pages = div[0].select('.//li/a/@href').extract()
            if pages and response.meta['do_pagination']:
                for page in pages:
                    log.msg(">>>>>>>>>>>>>>>>>>>>>>>>>>>> PAGE >>> %s" % page)
                    yield Request(
                            url=page,
                            callback=self.parse_products,
                            meta={'do_pagination': False})

        products = hxs.select('//ul[@class="productList"]/li/div/h3/a/@href').extract()
        for product in products:
            yield Request(
                    url=product,
                    callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//tr[@style="background: #FAFAFA; border-bottom: 1px dotted #CCC;"]')
        for product in products:
            name = product.select('td/span[@class="prod_big"]/text()')[0].extract()

            try:
                price = product.select('td[@class="aligncentre"]/span[contains(@class, "prod_big")]/text()')[0].extract()
            except:
                log.msg(">>> ERROR!!! >>> NO PRICE >>> %s" % name)

            loader = ProductLoader(item=Product(), selector=product)
            loader.add_value('name', name)
            loader.add_value('url', response.url)
            loader.add_value('price', price)
            loader.add_xpath('sku', './/span[@class="code_txt"]/text()', re='code: (.*)')
            loader.add_xpath('identifier', './preceding-sibling::input[@name="productId"]/@value')
            yield loader.load_item()
