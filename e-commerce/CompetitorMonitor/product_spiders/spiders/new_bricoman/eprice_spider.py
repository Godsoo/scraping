import os
import re
import json
import csv
import urlparse

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.utils import extract_price_eu
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class EpriceSpider(BaseSpider):
    name = 'newbricoman-eprice.it'
    allowed_domains = ['eprice.it']

    start_urls = ['http://www.eprice.it/search/sp=/casa-cucina/arredo-e-decorazioni/zanzariere',
                  'http://www.eprice.it/s/casa-cucina/bagno',
                  'http://www.eprice.it/s/casa-cucina/camera-da-letto',
                  'http://www.eprice.it/s/casa-cucina/illuminazione',
                  'http://www.eprice.it/search/sp=/casa-cucina/sicurezza-automazione-casa',
                  'http://www.eprice.it/s/elettrodomestici/climatizzazione',
                  'http://www.eprice.it/s/brico-giardino-animali/Utensili',
                  'http://www.eprice.it/s/casa-cucina/illuminazione', 
                  'http://www.eprice.it/s/brico-giardino-animali/materiale-elettrico',
                  'http://www.eprice.it/s/brico-giardino-animali/falegnameria',
                  'http://www.eprice.it/s/brico-giardino-animali/giardinaggio',
                  'http://www.eprice.it/s/auto-moto-nautica/nautica',
                  'http://www.eprice.it/s/auto-moto-nautica/auto-e-moto',
                  'http://www.eprice.it/s/brico-giardino-animali/arredo-giardino']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//div[@class="box_grigio"]/div[@class="box_center"]/ul[@class="listBlueArrow"]/li/a/@href').extract()
        for category in categories:
            cat_url = urljoin_rfc(base_url, category)
            yield Request(cat_url)

        products = hxs.select('//div[@id="esempioLista"]/form')
        if products:
            for product in products:
                l = ProductLoader(item=Product(), selector=product)
                l.add_xpath('identifier', 'div/div[@class="item"]/input[@name="sku"]/@value')
                l.add_xpath('name', 'div/div[@class="item"]/div/a/span[@class="itemName"]/text()')
                url = product.select('div/div[@class="item"]/div/a[@class="linkTit"]/@href').extract()
                l.add_value('url', urljoin_rfc(base_url, url[0]))
                l.add_xpath('sku', 'div/div[@class="item"]/div/p/span[@class="codVen"]/text()')
                l.add_xpath('brand', 'div/div[@class="item"]/div/a/span[@class="itemBrand"]/text()')
                l.add_xpath('image_url', 'div/div[@class="item"]/div/a[@class="linkImg"]/img/@src')
                l.add_xpath('category', '//h1[@itemprop="name"]/text()')
                price = product.select('div/div[@class="item"]/div/span[@class="itemPrice"]/text()').extract()
                price = extract_price_eu(price[0]) if price else 0
                l.add_value('price', price)
                out_of_stock = product.select('div/div[@class="item"]/div/p/strong[text()="NON DISPONIBILE"]').extract()
                if out_of_stock:
                    l.add_value('stock', 0)
                yield l.load_item()

        pages = hxs.select('//div[@class="pagNum"]/a/@href').extract()
        for page_url in pages:
            yield Request(''.join(page_url.split()))
