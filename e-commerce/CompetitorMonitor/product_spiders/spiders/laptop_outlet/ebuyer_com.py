import os
import csv

from decimal import Decimal
from urlparse import urljoin
from urllib import quote as url_quote

from scrapy import Spider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


HERE = os.path.abspath(os.path.dirname(__file__))

class EbuyerSpider(Spider):
    name = 'laptop_outlet-ebuyer.com'
    allowed_domains = ['ebuyer.com']

    download_timeout = 60

    csv_file = os.path.join(HERE, 'laptop_outlet_products.csv')

    def start_requests(self):
        with open(self.csv_file) as f:
            reader = csv.DictReader(f)
            for row in reader:
                search = row['Sku Number']
                self.log('Searching: %s' % search)
                yield Request('http://www.ebuyer.com/search?q=%s' % search,
                              callback=self.parse_product,
                              meta={
                                  'handle_httpstatus_list': [404],
                                  'search_term': search,
                                  'sku': search,
                              })

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        many = hxs.select('//div[contains(@class,"product-listing")]//h3/a/@href').extract()
        if not many:
            many = hxs.select('//div[contains(@class,"listing-product")]//h3/a/@href').extract()
        if many:
            for url in many:
                yield Request(urljoin(get_base_url(response), url), callback=self.parse_product)
            return

        price = hxs.select('//span[@class="now"]/span[@itemprop="price"]/text()').extract()
        if not price:
            price = hxs.select('//div[@class="product-price"]//span[@itemprop="price"]/text()').extract()
        if not price:
            if response.meta.get('tries', 0) < 3:
                self.log("Try: %s. Retrying page: %s" % (response.meta.get('tries', 0) + 1, response.url))
                yield Request(response.url,
                              callback=self.parse_product,
                              dont_filter=True,
                              meta={
                                  'handle_httpstatus_list': [404],
                                  'tries': response.meta.get('tries', 0) + 1
                              })
                return
            else:
                self.log('Gave up trying: %s' % response.url)
                self.log('No price found on page: %s' % response.url)
                return
        else:
            price = price[0]

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_xpath('identifier', 'substring(//h2[@id="manu"]/@content, 5)')
        loader.add_xpath('identifier', '//strong[@itemprop="mpn"]/text()')
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1/text()')
        loader.add_value('price', extract_price(price))
        loader.add_xpath('sku', 'substring(//h2[@id="manu"]/@content, 5)')
        loader.add_xpath('sku', '//strong[@itemprop="mpn"]/text()')
        loader.add_xpath('category', '//div[contains(@class, "breadcrumb")]//a/span/text()')

        img = hxs.select('//img[@itemprop="image"]/@src').extract()
        if img:
            loader.add_value('image_url', urljoin(get_base_url(response), img[0]))

        loader.add_xpath('brand', '//div[@itemprop="brand"]/meta[@itemprop="name"]/@content')
        if loader.get_output_value('price') < 50:
            loader.add_value('shipping_cost', '2.99')
        else:
            loader.add_value('shipping_cost', 0)

        loader.add_xpath('stock', '//span[@itemprop="quantity"]/text()')

        yield loader.load_item()

