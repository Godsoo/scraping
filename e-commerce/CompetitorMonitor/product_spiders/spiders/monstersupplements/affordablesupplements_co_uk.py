import re
import urllib
from decimal import Decimal
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class AffordablesupplementsCoUkSpider(BaseSpider):
    name = 'affordablesupplements.co.uk'
    allowed_domains = ['affordablesupplements.co.uk']

    def __init__(self, *args, **kwargs):
        super(AffordablesupplementsCoUkSpider, self).__init__(*args, **kwargs)
        self.brands = []
 
    def start_requests(self):
        yield Request('http://www.affordablesupplements.co.uk/brands/#all-brands', callback=self.parse_brands)
        yield Request('http://www.affordablesupplements.co.uk', callback=self.parse_full)

    def parse_brands(self, response):
        hxs = HtmlXPathSelector(response)

        self.brands = hxs.select(u'//ul[@id="main-rotate"]//a/text()').extract()
        

    def parse_full(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select(u'//a[@title="Products"]/..//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product_list, meta=response.meta)

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select(u'//a[@class="category-image"]/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product_list, meta=response.meta)

        for url in hxs.select(u'//ul[@class="pager"]//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product_list, meta=response.meta)

        for url in hxs.select(u'//div[@class="quick-info"]//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product, meta=response.meta)

    def get_options(self, hxs):
        ids = hxs.select(u'//select[starts-with(@id,"attribute")]/option/@value').extract()
        names = hxs.select(u'//select[starts-with(@id,"attribute")]/option/text()').extract()
        return zip(ids, names)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('url', response.url)
        product_loader.add_xpath('name', u'//h1/text()')
        product_loader.add_xpath('category', u'//ul[@id="breadcrumb"]/li[3]/a/@title')
        product_loader.add_xpath('category', u'//ul[@id="breadcrumb"]/li[3]/text()')
        product_loader.add_xpath('price', u'//strong[@id="price-here"]/text()')

        product_loader.add_xpath('sku', u'normalize-space(substring-after(//li[contains(text(),"SKU:")]/text(), ":"))')
        product_loader.add_xpath('identifier', u'normalize-space(substring-after(//li[contains(text(),"SKU:")]/text(), ":"))')

        img = hxs.select(u'//div[@id="product-shot"]/a/@href').extract()
        if not img:
            img = hxs.select(u'//img[@id="main-shot"]/@src').extract()
        if img:
            product_loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

#product_loader.add_xpath('shipping_cost', '')
        name = product_loader.get_output_value('name').split()[0].lower()
        for brand in self.brands:
            if brand.split()[0].lower() == name:
                product_loader.add_value('brand', brand)
                break
 
        product = product_loader.load_item()
        options = self.get_options(hxs)
        if options:
            for opt_id, name in options:
                prod = Product(product)
                prod['name'] = prod['name'] + ' ' + name
                prod['identifier'] = prod['identifier'] + ':' + opt_id
                yield prod
        else:
            yield product

        for url in hxs.select(u'//option[starts-with(@value, "http")]/@value').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product, meta=response.meta)
