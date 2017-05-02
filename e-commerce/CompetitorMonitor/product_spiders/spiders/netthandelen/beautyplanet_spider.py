import os
import re
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.fuzzywuzzy import process
from product_spiders.fuzzywuzzy import fuzz

HERE = os.path.abspath(os.path.dirname(__file__))

class BeautyPlanetSpider(BaseSpider):
    name = 'beautyplanet.no'
    allowed_domains = ['beautyplanet.no']
    start_urls = ['http://www.beautyplanet.no/Kvinne/Varemerke.aspx',
                  'http://www.beautyplanet.no/Mann/Varemerke.aspx']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        brands = hxs.select('//div[@class="Mod5ColBody"]/table/tr/td/div/a')
        for brand in brands:
            url =  urljoin_rfc(get_base_url(response), brand.select('@href').extract()[0])
            yield Request(url, callback=self.parse_categories, meta={'brand':brand.select('text()').extract()[0]})

    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)
        meta = response.meta
        categories = hxs.select('//*[@id="PageMenu"]/div/a')
        for category in categories:
            url =  urljoin_rfc(get_base_url(response), category.select('@href').extract()[0])
            meta['category'] = category.select('text()').extract()[0]
            yield Request(url, callback=self.parse_products, meta=meta)

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        meta = response.meta
        products = hxs.select('//div[@class="ProductDisplay"]')
        for product in products:
            name = ''.join(product.select('div[@class="Info"]/div/h1/a/text()').extract())
            image_url = urljoin_rfc(get_base_url(response), product.select('div[@class="Image"]/a/img/@src').extract()[0])
            if name:
                brand = ''.join( product.select('div[@class="Info"]/div/h4/a/text()').extract())
                name = ' '.join((brand, name))
                variants = product.select('div[@class="Info"]/div[@class="Variants"]/a/@href').extract()
                if variants:
                    meta['name'] = name
                    meta['image_url'] = image_url
                    url = urljoin_rfc(get_base_url(response), variants[0])
                    yield Request(url, callback=self.parse_product_variants, meta=meta)
                else:
                    loader = ProductLoader(item=Product(), selector=product)
                    loader.add_value('name', name)
                    loader.add_value('brand', meta.get('brand',''))
                    loader.add_value('category', meta.get('category',''))

                    relative_url =  product.select('div[@class="Info"]/div/h1/a/@href').extract()[0]
                    identifier = relative_url.split('/prd')[1].split('.')[0]
                    loader.add_value('identifier', identifier)
                    loader.add_value('url', urljoin_rfc(get_base_url(response), relative_url))
                    price = ''.join(product.select('div[@class="Info"]/h3/span[@class="Price"]/text()').extract()).replace('.','').replace(',','.')
                    loader.add_value('price', price)
                    loader.add_value('image_url', image_url)
                    yield loader.load_item()

    def parse_product_variants(self, response):
        hxs = HtmlXPathSelector(response)
        meta = response.meta
        variants = hxs.select('//tr[td/span[@class="Price"]]')
        for variant in variants:
            price = variant.select('td/span[@class="Price"]/text()').extract()
            variant_name = variant.select('td/text()').extract()[1].strip()
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('name', meta.get('name','')+variant_name)
            loader.add_value('brand', meta.get('brand',''))
            loader.add_value('category', meta.get('category',''))

            identifier = response.url.split('/prd')[1].split('.')[0]
            loader.add_value('identifier', identifier+'-'+variant_name)
            loader.add_value('url', response.url)
            price = ''.join(price).replace('.','').replace(',','.')
            loader.add_value('price', price)
            loader.add_value('image_url', meta.get('image_url'))
            yield loader.load_item()  
