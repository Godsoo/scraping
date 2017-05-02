import re
import json

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class CameraProSpider(BaseSpider):
    name = 'camerapro.com.au'
    allowed_domains = ['camerapro.com.au']
    start_urls = ('http://www.camerapro.com.au',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//ul[@id="menu"]//li[@class="level1"]/a/@href').extract()
        for category_url in categories:
            yield Request(category_url, callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        category_name = hxs.select('//div[@class="breadcrumbs"]//strong/text()').extract()[0]
        # products = hxs.select('//div[@class="product-main-content"]/h2/a/@href').extract()
        products = hxs.select('//div[@class="product-shop"]//h2/a/@href').extract()
        for prod_url in products:
            yield Request(prod_url, callback=self.parse_product, meta={'category': category_name})

        next_url = hxs.select('//a[@class="next i-next"]/@href').extract()
        data_param = hxs.select('//a[@class="next i-next"]/@data-param').extract()
        if next_url and data_param:
            url = next_url[0] + data_param[0]
            yield Request(url, callback=self.parse_category)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        try:
            identifier = hxs.select('//div[@class="no-display"]/input[@name="product"]/@value').extract()[0]
        except:
            return
        l = ProductLoader(item=Product(), response=response)
        l.add_value('identifier', identifier)
        l.add_xpath('name', '//div[@class="product-name"]/h1/text()')
        l.add_value('category', response.meta['category'])
        l.add_xpath('brand', '//table[@id="product-attribute-specs-table"]//tbody/tr[th/text()="Manufacturer"]/td/text()')
        l.add_xpath('sku', '//p[@class="info-sku"]/span/text()')
        l.add_value('url', response.url)
        price = hxs.select('//div[@class="price-box"]//span[@class="price"]/text()').extract()
        if not price:
            price = hxs.select('//span[@class="specialPrice"]/text()').re(r'[\d.,]+')
        # if not price:
        #    price = hxs.select('//div[@class="ZonePrix"]/div[@class="prix"]/strong/text()').extract()
        # price = ''.join(price[0].strip().split()).replace(',','.') if price else 0
        l.add_value('price', price[0])
        l.add_xpath('image_url', '//div[@class="product-img-box"]//li[@class="active"]/a[@id="zoom1"]/img/@src')

        out_stock = hxs.select('//div[@class="product-atributes-inner"]/*[contains(@class, "availability") and contains(@class, "out-of-stock")]')
        if out_stock:
            l.add_value('stock', 0)

        yield l.load_item()
