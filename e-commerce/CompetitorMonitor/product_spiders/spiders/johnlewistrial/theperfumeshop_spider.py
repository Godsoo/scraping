import os
import shutil
from scrapy import signals
from scrapy import log
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from scrapy.xlib.pydispatch import dispatcher

from product_spiders.spiders.BeautifulSoup import BeautifulSoup
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class ThePerfumeShopSpider(BaseSpider):
    name = 'johnlewis-trial-theperfumeshop.com'
    allowed_domains = ['theperfumeshop.com']
    start_urls = [
          'http://www.theperfumeshop.com/fcp/categorylist/womens/fragrances?resetFilters=true',
          'http://www.theperfumeshop.com/fcp/categorylist/mens/fragrances?resetFilters=true']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//div[@id="productsCont"]/div/a/@href').extract()
        for product in products:
            yield Request(product, callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//table[@id="productOptions"]/tbody/tr')
        for product in products:
            loader = ProductLoader(item=Product(), selector=product)
            loader.add_xpath('name', 'td/div[@class="skuInfo"]/h3/a/text()')
            sku = product.select('td/a/img/@data-sku').extract()[0]
            loader.add_value('sku', sku)
            loader.add_value('identifier', sku)
            category = hxs.select('//ul[@id="breadcrumb"]/li/a/text()').extract()
            category = category[-1] if category else ''
            loader.add_value('category', category)
            loader.add_xpath('brand', '//h2[@class="sirf-replaced"]/text()')
            loader.add_xpath('url', 'td/div[@class="skuInfo"]/h3/a/@href')
            price = product.select('td[@class="priceCont"]/p[@class="onlyPrice"]/strong/text()').extract()
            if price:
                price = price[0]
            else:
                price = product.select('td[@class="priceCont"]/p[@class="nowPrice"]/strong/text()').extract()
                if price:
                    price = price[0]
            loader.add_value('price', price)
            if not price:
                loader.add_value('stock', 0)

            item = loader.load_item()
            yield Request(item['url'], callback=self.parse_image, meta={'item': item})

    def parse_image(self, response):
        hxs = HtmlXPathSelector(response)
        item = response.meta['item']
      
        image_url = hxs.select('//img[@id="mainProductImage"]/@src').extract()
        item['image_url'] = urljoin_rfc(get_base_url(response), image_url[0]) if image_url else ''
        yield item
