import csv
import os
import copy
import re

from scrapy.spider import BaseSpider
# from scrapy.contrib.spiders import SitemapSpider
from scrapy.selector import HtmlXPathSelector, XmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy.http.cookies import CookieJar
from scrapy.utils.response import open_in_browser

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from decimal import Decimal
from utils import extract_price

HERE = os.path.abspath(os.path.dirname(__file__))

class SpazioIdroSpider(BaseSpider):
    name = 'newbricoman-spazioidro.it'
    allowed_domains = ['spazioidro.it']
    start_urls = ('http://www.spazioidro.it/sitemap.xml',)

    '''
    sitemap_rules = [
        ('/Articolo', 'parse_product'),
    ]
    '''

    def parse(self, response):
        urls = re.findall(r'<loc>(.*/Articolo.*)</loc>', response.body)
        for url in urls:
            yield Request(url, callback=self.parse_product)

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        name = hxs.select('//span[@class="ArTit"]//text()').extract()[0]
        name = " ".join(name.split())
        loader.add_value('name', name)
        loader.add_xpath('sku', '//span[@id="MainContent_ngpArticolo_lblARCd_AR"]/text()')
        price = hxs.select('//span[@id="MainContent_ngpArticolo_lblPrezzoScontato"]/text()')[0].extract()
        price = price.replace('.', '').replace(',', '.')
        loader.add_value('price', price)
        loader.add_xpath('brand', '//span[@id="MainContent_ngpArticolo_lblARMarcaDescrizione"]/text()')
        loader.add_xpath('category', '//span[@id="MainContent_ngpArticolo_lblCd_ARGruppo2"]/text()')
        image_url = hxs.select('//div[@id="gallery"]/img/@src')
        if not image_url:
            image_url = hxs.select('//div[@id="gallery"]/input/@src')

        image_url = image_url[0].extract()
        if not image_url.strip().endswith('noimage.png'):
            loader.add_value('image_url', urljoin_rfc(base_url, image_url))
        if hxs.select('//div[@class="art-light-red"]'):
            loader.add_value('stock', 0)
        loader.add_value('url', response.url)
        loader.add_value('identifier', response.url.split('id=')[1])

        price = extract_price(price)

        if price < Decimal(100):
            loader.add_value('shipping_cost', '15.00')
        elif price < Decimal(251):
            loader.add_value('shipping_cost', '30.00')
        elif price < Decimal(751):
            loader.add_value('shipping_cost', '40.00')
        elif price < Decimal(1000):
            loader.add_value('shipping_cost', '60.00')
        else:
            loader.add_value('shipping_cost', '100.00')

        yield loader.load_item()
