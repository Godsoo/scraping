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

HERE = os.path.abspath(os.path.dirname(__file__))


class ExpertTechnomarktSpider(ProductCacheSpider):
    name = 'expert-technomarkt.de'
    allowed_domains = ['expert-technomarkt.de']
    start_urls = ('http://www.expert-technomarkt.de/index.php?tpl=&_artperpage=100&cl=search&searchparam=logitech&query=',)

    map_products_csv = os.path.join(HERE, 'logitech_map_products.csv')
    map_price_field = 'map'
    map_join_on = [('sku', 'mpn'), ('sku', 'ean13')]

    def _start_requests(self):
        yield Request('http://www.notebooksbilliger.de/logitech+k830+illuminated+living+room+keyboard/eqsqid/dc034145-ba5e-417d-b751-99748adbb8b8', meta={'product':Product()}, callback=self.parse_product)

    def start_requests(self):

        for url in self.start_urls:
            yield Request(url)

        with open(HERE + '/logitech_extra_products.csv') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['ExpertTechno'] != 'No Match':
                    product = Product()
                    request = Request(row['ExpertTechno'], callback=self.parse_product, meta={'sku':row['sku'], 'brand':row['brand']})
                    yield self.fetch_product(request, product)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for productxs in hxs.select('//div[@class="single_article"]'):
            product = Product()
            product['price'] = extract_price_eu(''.join(productxs.select('.//div[@class="price"]/img/@alt').extract()))
            if productxs.select('.//div[@class="status"]/img[contains(@pagespeed_url_hash,"2593193988")]'):
                product['stock'] = '0'
            else:
                product['stock'] = '1'

            request = Request(urljoin_rfc(get_base_url(response), productxs.select('substring-before(./a/@href,"?")').extract()[0]), callback=self.parse_product, meta=response.meta)
            yield self.fetch_product(request, product)

	for page in hxs.select('//div[@class="paging"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), page))

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=response.meta['product'], selector=hxs)
        loader.add_xpath('identifier', '//input[@name="anid"]/@value')
#        loader.add_xpath('sku', '//span[contains(text(),"Herstellernummer:")]/span/text()')
        loader.add_value('url', response.url)
        loader.add_value('name', u''.join(hxs.select('//h1[@id="test_product_name"]/text()').extract()).strip().replace('\n', ' '))

        sku = response.meta.get('sku', '')
        if sku:
            loader.add_value('sku', sku)
            price = hxs.select('//form/div[@class="price"]/img/@title').extract()
            price = price[0] if price else '0'
            loader.add_value('price', extract_price_eu(price))
            out_of_stock = hxs.select('//form/div[@class="price"]/img/@title').extract()
            if out_of_stock:
                loader.add_value('stock', '0')
            else:
                loader.add_value('stock', '1')
            loader.add_value('brand', response.meta.get('brand', ''))
        else:
	    try:
                loader.add_value('sku', re.search(r'\b([A-Z]{1,2})*[\+\-0-9]{2,10}', loader.get_output_value('name')).group(0))
            except: pass
            loader.add_value('brand', 'Logitech')

        loader.add_value('category', response.url.split('/')[-2])

        img = hxs.select('//td[@id="magiczoomplushook"]//a/@href').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        loader.add_value('shipping_cost', '0')
        yield loader.load_item()
