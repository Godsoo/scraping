import re
from decimal import Decimal
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class GlostertoolingSpider(BaseSpider):
    name = 'glostertooling'
    allowed_domains = ['ebay.co.uk']

    def __init__(self, *args, **kwargs):
        super(GlostertoolingSpider, self).__init__(*args, **kwargs)
 
    def start_requests(self):
        yield Request('http://stores.ebay.co.uk/Gloster-Tooling/_i.html?rt=nc&_sid=26428065&_trksid=p4634.c0.m14.l1513', callback=self.parse_product_list)

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select(u'//td[@class="details"]//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product, meta=response.meta)

        for url in hxs.select(u'//table[@class="pager"]//td[@class="next"]//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product_list, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('url', response.url)
        product_loader.add_xpath('name', u'//h1/text()')
        product_loader.add_xpath('price', u'//span[@itemprop="price"]/text()')
        product_loader.add_xpath('category', u'(//a[@class="thrd"])[2]/text()')

        img = hxs.select(u'//img[@id="icImg"]/@src').extract()[0]
        product_loader.add_value('image_url', urljoin_rfc(get_base_url(response), img))

        product_loader.add_xpath('sku', u'//div[@class="u-flR"]/text()')
        product_loader.add_xpath('identifier', u'//div[@class="u-flR"]/text()')
#product_loader.add_xpath('brand', '')
        shipping_cost = hxs.select(u'//span[@id="fshippingCost"]/span/text()').extract()
        if not shipping_cost:
            pass # Not specified
        elif shipping_cost[0].lower().strip() == 'free':
            product_loader.add_value('shipping_cost', 0)
        else:
            product_loader.add_value('shipping_cost', extract_price(shipping_cost[0]))

        product = product_loader.load_item()
        options = hxs.select(u'//option[starts-with(@id,"msku-opt-")]')
        if options:
            for opt in options:
                prod = Product(product)
                prod['name'] = prod['name'] + ' ' + opt.select(u'normalize-space(./text())').extract()[0]
                prod['identifier'] = prod['identifier'] + ':' + opt.select(u'./@value').extract()[0]
                yield prod
        else:
            yield product
