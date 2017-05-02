import csv
import os
import copy

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, url_query_parameter
from scrapy.http.cookies import CookieJar

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class HouraSpider(BaseSpider):
    name = 'legofrance-houra.fr-lego'
    allowed_domains = ['houra.fr']
    start_urls = ('http://www.houra.fr/catalogue/jouets-multimedia/lego/voir-tous-les-produits-B1460658-1.html',)

    # download_delay = 0.1

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//div[@class="bloc_article_float"]')
        for product in products:
            meta = {}
            meta['category'] = product.select('table/tr/td//div[@class="marque trunc"]/@title').extract()[0]
            meta['name'] = product.select('table/tr/td//div[@class="nom trunc"]/div/span/a/text()').extract()[0].strip()
            meta['sku'] = meta['name'].split('-')[0]
            meta['brand'] = "LEGO"
            meta['price'] = product.select('table/tr/td//div[@class="prix"]/text()').extract()[0].strip().replace(',', '.')
            url = product.select('table/tr/td//div[@class="nom trunc"]/div/span/a/@href').extract()[0].strip()
            image = product.select('table/tr/td[contains(@class, "photo")]//img/@src').extract()[0].replace('MED', 'ZOO')

            l = ProductLoader(item=Product(), response=response)
            l.add_value('identifier', url_query_parameter(url, 'id_article'))
            l.add_value('name', meta['category'] + ' ' + meta['name'])
            l.add_value('category', meta['category'])
            l.add_value('brand', meta['brand'])
            l.add_value('sku', meta['sku'])
            l.add_value('url', url)
            l.add_value('price', meta['price'])
            l.add_value('image_url', image)

            yield l.load_item()

            # yield Request(url, callback=self.parse_product, meta=meta)
        next = hxs.select('//a[text()="Page suivante "]/@href').extract()
        if next:
            yield Request(next[0])

    '''
    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        meta = response.meta
        l = ProductLoader(item=Product(), response=response)
        l.add_value('identifier', meta['identifier'])
        l.add_value('name', meta['category'] + ' ' + meta['name'])
        l.add_value('category', meta['category'])
        l.add_value('brand', meta['brand'])
        l.add_value('sku', meta['identifier'])
        l.add_value('url', response.url)
        l.add_value('price', meta['price'])
        image = hxs.select('//div[@class="fa_photo  "]/a/img/@src').extract()
        if image:
            image = image[0]
        else:
            image = hxs.select('//div[@id="container_photos"]/div[@class="fa_photo decallage_photo_big "]/a[@class="zoom"]/img/@src').extract()[0]
        l.add_value('image_url', image)
        yield l.load_item()
    '''
