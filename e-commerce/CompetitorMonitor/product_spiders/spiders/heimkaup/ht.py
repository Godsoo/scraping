import re
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

from heimkaupitems import HeimkaupProduct as Product

class HtSpider(ProductCacheSpider):
    name = 'heimkaup-ht'
    allowed_domains = ['ht.is']
    start_urls = ('http://ht.is',)

    def _start_requests(self):
        yield Request('http://www.banneke.com/Whisky/Whiskey/International/Amrut_Malt_Whisky_aus_Indien_46_0.70', callback=self.parse_product, meta={'product': Product()})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for cat in hxs.select('//div[contains(@class, "categories")]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), cat), callback=self.parse)
        for cat in hxs.select('//div[@class="paginator"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), cat), callback=self.parse)

        for productxs in hxs.select('//div[contains(@class, "product-item")]'):
            product = Product()
            product['price'] = extract_price_eu(''.join(productxs.select('.//span[@class="price"]/text()').extract()))

            if productxs.select('.//div[contains(@class, "lager1")]'):
                product['stock'] = 1
            else:
                product['stock'] = 0

            request = Request(urljoin_rfc(get_base_url(response), productxs.select('.//h4/a/@href').extract()[0]), callback=self.parse_product, meta=response.meta)
            yield self.fetch_product(request, self.add_shipping_cost(product))

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=response.meta['product'], selector=hxs)

        loader.add_xpath('identifier', '//input[@name="productId"]/@value')
        loader.add_xpath('sku', '//span[@class="productNr"]/text()')
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h2[@class="header"]/text()[last()]')

        loader.add_xpath('category', '//div[contains(@class, "categories")]//li[@class="active"]/a/text()')

        img = hxs.select('//div[@class="theimg"]//img/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        loader.add_xpath('brand', '//h2[@class="header"]/text()[1]')
        yield self.add_shipping_cost(loader.load_item())

    def add_shipping_cost(self, item):
        item['shipping_cost'] = 0
        return item
