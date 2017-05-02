import re
from decimal import Decimal
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class MachineDroCoUkSpider(BaseSpider):
    name = 'machine-dro.co.uk'
    allowed_domains = ['machine-dro.co.uk']

    def __init__(self, *args, **kwargs):
        super(MachineDroCoUkSpider, self).__init__(*args, **kwargs)
 
    def start_requests(self):
        yield Request('http://machine-dro.co.uk/', callback=self.parse_full)

    def parse_full(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select(u'//div[@class="sidebox-categories-wrapper"]//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product_list)

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select(u'//div[@class="subcategories"]//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product_list, meta=response.meta)

        for url in hxs.select(u'//div[@class="product-description"]/a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product, meta=response.meta)

        for url in hxs.select(u'//a[@class="pagination-link"]/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product_list, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('url', response.url)
        product_loader.add_xpath('name', u'//h1/text()')
        product_loader.add_xpath('price', u'//span[starts-with(@id,"line_product_price_")]//span[starts-with(@id,"sec_") and @class="list-price"]/text()')
        product_loader.add_xpath('category', u'//div[@class="bc-text"]/a[2]/text()')

        img = hxs.select(u'//div[@class="product-image"]/a/@href').extract()[0]
        product_loader.add_value('image_url', urljoin_rfc(get_base_url(response), img))

        product_loader.add_xpath('sku', u'//span[starts-with(@id,"product_code_")]/text()')
        product_loader.add_xpath('identifier', u'//span[starts-with(@id,"product_code_")]/text()')
#product_loader.add_xpath('brand', '')
#product_loader.add_xpath('shipping_cost', '')

        yield product_loader.load_item()
