# coding=utf-8
import re

from scrapy import log
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector, XmlXPathSelector
from scrapy.http import Request  # , HttpResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import (
    Product, ProductLoaderWithNameStrip as ProductLoader)

from scrapy.contrib.spiders import SitemapSpider

class EdiloisirSpyder(SitemapSpider):
    name = "ediloisir.com"
    sitemap_urls = ['http://www.ediloisir.com/media/sitemap/www/sitemap.xml']
    allowed_domains = ["ediloisir.com"]
    # start_urls = ('http://www.ediloisir.com/',)
    # namespaces = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    '''
    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//ul[@class="menu"]/li/a/@href').extract()

        for url in categories:
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_categories)

    def parse_categories(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        cats = hxs.select(('//div[@id="img_cat"]/a/@href')).extract()
        for url in cats:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_categories)

        for product in self.parse_products(hxs, response):
            yield product

    def parse_products(self, hxs, response):
        base_url = get_base_url(response)
        for product in hxs.select('//div[@id="titre_pdt"]/..'):
            loader = ProductLoader(selector=product, item=Product())
            loader.add_xpath('name', './/h2/text()')
            url = product.select('.//div[@id="img_pdt"]/a/@href').extract()[0]
            url = urljoin_rfc(base_url, url)
            loader.add_value('url', url)
            price = u''.join(product.select(".//a[@class='prix_normal']//text()").extract())
            loader.add_value('price', price)
            yield loader.load_item()
    '''

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        name = hxs.select('//div[@class="product-main-info"]/div[@class="product-name"]/h1/text()').extract()
        if name:
            product_loader = ProductLoader(item=Product(), selector=hxs)
            product_loader.add_value('name', name[0])
            price_int = ''.join(re.findall(r'\d+', hxs.select('//div[@class="price-box"]//span[contains(@id,'
                                                              '"product-price")]/text()').extract()[0]\
                                           .strip()))
            if not price_int:
                price_int = ''.join(re.findall(r'\d+', hxs.select('//div[@class="price-box"]//span[contains(@id, '
                                                                  '"product-price")]/span[@class="price"]/text()')
                                               .extract()[0].strip()))
                price_decimal = hxs.select('//div[@class="price-box"]//span[contains(@id,'
                                           '"product-price")]/span[@class="price"]/span[@class="price-decimal"]/text()')\
                                           .extract()[0].strip()
            else:
                price_decimal = hxs.select('//div[@class="price-box"]//span[contains(@id,'
                                           '"product-price")]/span[@class="price-decimal"]/text()')\
                                           .extract()[0].strip()
            price = (price_int + price_decimal).replace(',', '.')
            product_loader.add_value('price', price)
            product_loader.add_value('url', response.url)
            product_loader.add_xpath('identifier', '//div[@class="no-display"]/input[@name="product"]/@value')

            yield product_loader.load_item()
