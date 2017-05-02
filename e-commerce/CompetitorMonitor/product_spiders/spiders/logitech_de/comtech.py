import re
import os
import csv
import json
import urlparse

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price_eu
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.base_spiders.prodcache import ProductCacheSpider
from decimal import Decimal

HERE = os.path.abspath(os.path.dirname(__file__))


class ComtechSpider(ProductCacheSpider):
    name = 'comtech.de'
    allowed_domains = ['comtech.de']
    # Site has bugs in pagination, try out all ways to extract as many products as possible
    start_urls = (
            'http://www.comtech.de/shopware.php/sViewport,SwpFindologic/sAction,search/sSearch,logitech/order,none/count,12',
            'http://www.comtech.de/shopware.php/sViewport,SwpFindologic/sAction,search/sSearch,logitech/order,none/count,24',
            'http://www.comtech.de/shopware.php/sViewport,SwpFindologic/sAction,search/sSearch,logitech/order,none/count,36',
            'http://www.comtech.de/shopware.php/sViewport,SwpFindologic/sAction,search/sSearch,logitech/order,none/count,48',)

    map_products_csv = os.path.join(HERE, 'logitech_map_products.csv')
    map_price_field = 'map'
    map_join_on = [('sku', 'mpn'), ('sku', 'ean13')]

    def _start_requests(self):
        yield Request('http://www.comtech.de/Computer-und-Zubehoer/Eingabegeraete/Maeuse/Logitech-Performance-Maus-MX', meta={'product':Product()}, callback=self.parse_product)

    def start_requests(self):

        for url in self.start_urls:
            yield Request(url)

        with open(HERE + '/logitech_extra_products.csv') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['ComTech'] != 'No Match':
                    product = Product()
                    request = Request(row['ComTech'], callback=self.parse_product, meta={'sku':row['sku'], 'brand':row['brand']})
                    yield self.fetch_product(request, product)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for productxs in hxs.select('//div[@class="artbox"]'):
            product = Product()
            product['price'] = extract_price_eu(''.join(productxs.select('.//span[@class="price"]//text()').extract()))
            if product['price'] == 0:
                product['stock'] = '0'
            else:
                product['stock'] = '1'

            request = Request(urljoin_rfc(get_base_url(response), productxs.select('.//a[@class="title"]/@href').extract()[0]), callback=self.parse_product, meta=response.meta)
            yield self.fetch_product(request, product)

        for page in hxs.select('//div[@class="paging"]//a[@class="navi more"]/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), page))
            break  # First link only

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=response.meta['product'], selector=hxs)
        loader.add_xpath('identifier', '//span[@itemprop="identifier"]/text()')

        sku = response.meta.get('sku', '')
        if sku:
            loader.add_value('sku', sku)
            price = hxs.select('//div[@itemprop="offerDetails"]/strong[@class="red"]/text()').extract()
            price = price[0] if price else '0'
            loader.add_value('price', extract_price_eu(price))
            if price == '0':
                loader.add_value('stock', '0')
            else:
                loader.add_value('stock', '1')
            loader.add_value('brand', response.meta.get('brand', ''))
        else:
            loader.add_xpath('sku', '//span[@itemprop="identifier" and starts-with(@content,"mpn:")]/text()')
            if not loader.get_output_value('sku'):
                loader.add_xpath('sku', '//span[@itemprop="identifier"]/text()')
            loader.add_value('brand', 'Logitech')


        loader.add_value('url', response.url)
        loader.add_xpath('name', '//*[@itemprop="name"]//text()')

        loader.add_xpath('category', 'normalize-space(//div[@id="breadcrumb"]/a[position()=last()]//text())')

        img = hxs.select('//a[@id="zoom1"]/@href').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))


        loader.add_value('shipping_cost', '0')

        yield loader.load_item()
