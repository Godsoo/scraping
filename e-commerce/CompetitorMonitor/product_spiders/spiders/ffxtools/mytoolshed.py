# -*- coding: utf-8 -*-


"""
- Original assembla ticket #: 3918
- Run Scrapy >= 0.15 for correct operation (cookiejar feature)
- Prices including Tax
- It uses cache by using previous crawl data and updating only prices and stock status from product lists.
  Enter to product page only for new products, this is only for some fields like SKU which
  are not in products list page
"""


__author__ = 'Emiliano M. Rudenick (emr.frei@gmail.com)'


import os
import re
import pandas as pd
from decimal import Decimal
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.config import DATA_DIR
from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader,
)


class MyToolShedSpider(BaseSpider):
    name = 'ffxtools-my-tool-shed.co.uk'
    allowed_domains = ['my-tool-shed.co.uk']
    start_urls = ['http://www.my-tool-shed.co.uk/sitemap.php']

    user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10; rv:33.0) Gecko/20100101 Firefox/33.0'

    def __init__(self, *args, **kwargs):
        super(MyToolShedSpider, self).__init__(*args, **kwargs)

        self._current_cookie = 0
        self.products_cache_filename = ''
        self.products_cache = None

    def start_requests(self):
        if hasattr(self, 'prev_crawl_id'):
            self.products_cache_filename = os.path.join(DATA_DIR, '%s_products.csv' % self.prev_crawl_id)
            self.products_cache = pd.read_csv(self.products_cache_filename, dtype=pd.np.str)
            self.products_cache = self.products_cache.where(pd.notnull(self.products_cache), None)
            self.products_cache['viewed'] = False

        for url in self.start_urls:
            yield Request(url)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//td[@class="columnMiddle"]//a/@href').extract()
        for url in categories:
            self._current_cookie += 1
            yield Request(urljoin_rfc(base_url, url),
                          meta={'cookiejar': self._current_cookie},
                          callback=self.parse_list)

    def parse_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        products = hxs.select('//td[@class="productListing-column"]')
        for product_xs in products:
            product_cached_found = False
            product_price = product_xs.select('.//div[@class="productListingPrice"]').re(r'[\d,.]+')
            product_url = product_xs.select('.//div[@class="productListingName"]//a/@href').extract()
            product_identifier = product_xs.select('.//div[@class="productListingName"]//a/@href').re(r'/p(\d+)/')
            if product_identifier and product_price and (self.products_cache is not None):
                cached_item = self.products_cache[self.products_cache['identifier'] == product_identifier[0]]
                if not cached_item.empty:
                    product_cached_found = True
                    cached_item_dict = dict(cached_item.iloc[0])
                    del cached_item_dict['viewed']
                    cached_product = Product(cached_item_dict)
                    cached_product['price'] = Decimal(product_price[0].replace(',', ''))
                    del cached_product['dealer']
                    if cached_product['name'] is None:
                        del cached_product['name']
                    if cached_product['category'] is None:
                        del cached_product['category']
                    if cached_product['shipping_cost']:
                        cached_product['shipping_cost'] = Decimal(cached_product['shipping_cost'].replace(',', ''))
                    else:
                        del cached_product['shipping_cost']
                    del cached_product['stock']
                    self.products_cache['viewed'].loc[cached_item.index] = True
                    yield cached_product

            if not product_cached_found:
                yield Request(urljoin_rfc(base_url, product_url[0]),
                              callback=self.parse_product,
                              meta=response.meta)

        pages = map(lambda u: urljoin_rfc(base_url, u), set(hxs.select('//*[@class="pageResults"]/@href').extract()))
        for url in pages:
            yield Request(url, callback=self.parse_list, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        product_identifier = re.findall(r'/p(\d+)/', response.url)
        product_name = hxs.select('//h1[@itemprop="name"]/text()').extract()
        product_price = hxs.select('//*[@itemprop="price"]/text()').extract()
        product_image = hxs.select('//meta[@property="og:image"]/@content').extract()
        product_brand = hxs.select('//*[@itemprop="brand"]/*[@itemprop="name"]/text()').extract()
        product_in_stock = bool(hxs.select('//*[@itemprop="availability"]').re(r'InStock'))
        product_sku = hxs.select('//*[contains(text(), "Barcode:")]/*[@class="prodInfo_brand_blue"]/text()').extract()
        product_category = hxs.select('//*[@class="breadcrumb"]//a/text()').extract()[1:]

        l = ProductLoader(item=Product(), response=response)
        l.add_value('identifier', product_identifier)
        l.add_value('name', product_name)
        l.add_value('price', product_price)
        l.add_value('url', response.url)
        l.add_value('category', product_category)
        if product_image:
            l.add_value('image_url', urljoin_rfc(base_url, product_image[0]))
        if product_brand:
            l.add_value('brand', product_brand)
        if product_sku:
            l.add_value('sku', product_sku)
        if not product_in_stock:
            l.add_value('stock', 0)

        product_item = l.load_item()
        if ('price' in product_item) and product_item['price'] and product_item['price'] > Decimal('100'):
            product_item['shipping_cost'] = Decimal('4.98')

        yield product_item
