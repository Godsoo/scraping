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

class MyTheresaSpider(BaseSpider):
    name = 'mytheresa.com'
    allowed_domains = ['mytheresa.com']
    start_urls = [
        'http://www.mytheresa.com/en-de/bags.html?allproducts=yes&designer=3741|3755|3802|4889|5050|3732',
        'http://www.mytheresa.com/en-de/sale/bags.html?designer=3741|3755|3802|4889|5050|3732',
        'http://www.mytheresa.com/en-de/shoes.html?allproducts=yes&designer=3739|3767|3768|3769|3813|3732|5050',
        'http://www.mytheresa.com/en-de/sale/shoes.html?designer=3739|3767|3768|3769|3813|3732|5050',
        'http://www.mytheresa.com/en-de/accessories.html?allproducts=yes&designer=3734|3735|3737|3739|3869',
        'http://www.mytheresa.com/en-de/sale/accessories.html?designer=3734|3735|3737|3739|3869',
        'http://www.mytheresa.com/en-de/clothing/dresses.html?designer=3733|3734|3735|3841|3856',
        'http://www.mytheresa.com/en-de/sale/clothing/dresses.html?designer=3733|3734|3735|3841|3856',
        'http://www.mytheresa.com/en-de/clothing/coats.html?designer=3733|3734|3735|3841|3856',
        'http://www.mytheresa.com/en-de/sale/clothing/coats.html?designer=3733|3734|3735|3841|3856',
        'http://www.mytheresa.com/en-de/clothing/knitwear.html?designer=3733|3734|3735|3841|3856',
        'http://www.mytheresa.com/en-de/sale/clothing/knitwear.html?designer=3733|3734|3735|3841|3856',
        'http://www.mytheresa.com/en-de/clothing/tops.html?designer=3733|3734|3735|3841|3856',
        'http://www.mytheresa.com/en-de/sale/clothing/tops.html?designer=3733|3734|3735|3841|3856',
        'http://www.mytheresa.com/en-de/clothing/jackets.html?designer=3733|3734|3735|3841|3856',
        'http://www.mytheresa.com/en-de/sale/clothing/jackets.html?designer=3733|3734|3735|3841|3856',
        'http://www.mytheresa.com/en-de/clothing/pants.html?designer=3733|3734|3735|3841|3856',
        'http://www.mytheresa.com/en-de/sale/clothing/pants.html?designer=3733|3734|3735|3841|3856',
        'http://www.mytheresa.com/en-de/clothing/skirts.html?designer=3733|3734|3735|3841|3856',
        'http://www.mytheresa.com/en-de/sale/clothing/skirts.html?designer=3733|3734|3735|3841|3856',
        'http://www.mytheresa.com/en-de/clothing/denim.html?designer=3733|3734|3735|3841|3856',
        'http://www.mytheresa.com/en-de/sale/clothing/denim.html?designer=3733|3734|3735|3841|3856',
        'http://www.mytheresa.com/en-de/clothing/shorts.html?designer=3733|3734|3735|3841|3856',
        'http://www.mytheresa.com/en-de/sale/clothing/shorts.html?designer=3733|3734|3735|3841|3856',
        'http://www.mytheresa.com/en-de/clothing/beachwear.html?designer=3733|3734|3735|3841|3856',
        'http://www.mytheresa.com/en-de/sale/clothing/beachwear.html?designer=3733|3734|3735|3841|3856',
        'http://www.mytheresa.com/en-de/clothing/leisurewear.html?designer=3733|3734|3735|3841|3856',
        'http://www.mytheresa.com/en-de/sale/clothing/leisurewear.html?designer=3733|3734|3735|3841|3856',
        'http://www.mytheresa.com/en-de/clothing/suits-jumpsuits.html?designer=3733|3734|3735|3841|3856',
        'http://www.mytheresa.com/en-de/sale/clothing/suits-jumpsuits.html?designer=3733|3734|3735|3841|3856',
        'http://www.mytheresa.com/en-de/clothing/tailoring.html?designer=3733|3734|3735|3841|3856',
        'http://www.mytheresa.com/en-de/sale/clothing/tailoring.html?designer=3733|3734|3735|3841|3856',
        'http://www.mytheresa.com/en-de/clothing/fur.html?designer=3733|3734|3735|3841|3856',
        'http://www.mytheresa.com/en-de/sale/clothing/fur.html?designer=3733|3734|3735|3841|3856',
    ]
    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        category = hxs.select('//div[@class="col-left sidebar"]//div[@class="block-title"]/h1/text()').extract()[0]

        products = hxs.select('//h3[@class="product-name"]/a/@href').extract()
        for product in products:
            yield Request(product, callback=self.parse_product, meta={'category':category})

        next = hxs.select('//a[@class="next i-next"]/@href').extract()
        if next:
            yield Request(next[0])

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        meta = response.meta

        name = hxs.select('//h1[@itemprop="name"]/text()').extract()[0]
        colour = hxs.select('//div[@itemprop="description"]//ul[contains(@class, "disc")'
            ' and contains(@class, "featurepoints")]/li[contains(text(), "colour name:")]/text()')\
            .re(r'name: (.*)')

        if colour:
            name = name.strip() + ' ' + colour[0].strip()

        loader = ProductLoader(response=response, item=Product())
        loader.add_xpath('identifier', '//input[@name="product"]/@value')
        loader.add_xpath('sku', '//h3[@class="sku-number"]/text()')
        loader.add_value('name', name)

        price = hxs.select('//p[@class="special-price"]/span[@class="price"]/text()').extract()
        if price:
            price = extract_price_eu(price[0])
        else:
            price = hxs.select('//span[@class="price"]/text()').extract()
            if price:
                price = extract_price_eu(price[0])
            else:
                price = 0

        loader.add_value('price', price)
        loader.add_value('url', response.url)
        loader.add_xpath('image_url', '//img[@id="main-image-image"]/@src')
        loader.add_xpath('brand', '//a[@itemprop="brand"]/text()')
        category = hxs.select('//div[@class="breadcrumbs"]/ul/li/a/span/text()').extract()[1]
        loader.add_value('category', meta['category'])
        loader.add_value('shipping_cost', 9)
        sold_out = hxs.select('//button[@class="btn-cart soldout"]')
        if sold_out:
            loader.add_value('stock', 0)
        yield loader.load_item()
