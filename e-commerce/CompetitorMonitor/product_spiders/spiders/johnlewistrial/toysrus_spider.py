import os
import re
import shutil
from scrapy import signals
from scrapy import log
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from scrapy.xlib.pydispatch import dispatcher

from johnlewisitems import JohnLewisMeta

from product_spiders.spiders.BeautifulSoup import BeautifulSoup
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class ToysRusSpider(BaseSpider):
    name = 'johnlewis-trial-toysrus.co.uk'
    allowed_domains = ['toysrus.co.uk']
    start_urls = [
          'http://www.toysrus.co.uk/browse/product/toys?topnav=Toys&fh_maxdisplaynrvalues_categories=-1',
          'http://www.toysrus.co.uk/browse/product/learning?topnav=Learning&fh_maxdisplaynrvalues_categories=-1',
          'http://www.toysrus.co.uk/browse/product/technology-gadgets?topnav=Technology+%26+Gadgets&fh_maxdisplaynrvalues_categories=-1']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//div[@id="searchFilter"]/ul[1]/li/a')
        for category in categories:
            url = urljoin_rfc(get_base_url(response), category.select('@href').extract()[0])
            category_name = category.select('text()').extract()[0].strip()
            if 'less' not in category_name:
                yield Request(url, callback=self.parse_brands, meta={'category': category_name})

    def parse_brands(self, response):
        hxs = HtmlXPathSelector(response)
        meta = response.meta
          
        brands = hxs.select('//li/a[contains(@href, "brands")]')
        for brand in brands:
            brand_name = brand.select('text()').extract()[0].strip()
            brand_url = brand.select('@href').extract()[0]
            meta['brand'] = brand_name
            yield Request(urljoin_rfc(get_base_url(response), brand_url), 
                          callback=self.parse_products, 
                          meta=meta)

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        meta = response.meta

        products = hxs.select('//tr[@class="under_best_match"]')
        for product in products:
            loader = ProductLoader(item=Product(), selector=product)
            loader.add_xpath('name', 'td/dl[@class="hproduct"]/dt/a/text()')
            sku = product.select('td/dl/dd[@class="reference_number"]/text()').extract()[0].strip()
            loader.add_value('sku', sku)
            loader.add_value('identifier', sku)
            url = urljoin_rfc(get_base_url(response), product.select('td/dl[@class="hproduct"]/dt/a/@href').extract()[0])
            loader.add_value('url', url)
            loader.add_value('brand', meta['brand'])
            loader.add_value('category', meta['category'])
            image_url = product.select('td/dl/dd[@class="product_image"]/a/@style').extract()
            image_url = re.search('(\'.*\')', image_url[0]).group(1) if image_url else ''
            loader.add_value('image_url', image_url)
            loader.add_xpath('price', 'td[@class="price_bucket"]/ul/li[@class="total_price"]/text()')
            item = loader.load_item()

            price_was = product.select('td//li[@class="old_price"]/strong[contains(text(), "Was")]/text()').extract()
            price_was = ' '.join(price_was[0].split()) if price_was else ''
            metadata = JohnLewisMeta()
            metadata['promotion'] = price_was
            item = loader.load_item()
            item['metadata'] = metadata

            if item['price']<30:
                item['shipping_cost'] = 4.95

            yield item
        next = hxs.select('//a[@title="Next"]/@href').extract()
        if next:
            url = urljoin_rfc(get_base_url(response), next[0])
            yield Request(url, callback=self.parse_products)
