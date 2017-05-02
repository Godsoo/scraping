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

class EpalSpider(ProductCacheSpider):
    name = 'heimkaup-epal'
    allowed_domains = ['epal.is']
    start_urls = ('http://www.epal.is/verslun/voruflokkar-vefverslun/',)

    def _start_requests(self):
        yield Request('http://www.banneke.com/Whisky/Whiskey/International/Amrut_Malt_Whisky_aus_Indien_46_0.70', callback=self.parse_product, meta={'product': Product()})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for cat in response.css('div.product-category a::attr(href)').extract():
            yield Request(urljoin_rfc(get_base_url(response), cat), callback=self.parse)
        for cat in response.css('a.page-number::attr(href)').extract():
            yield Request(urljoin_rfc(get_base_url(response), cat), callback=self.parse)

        for productxs in response.css('div.product'):
            product = Product()
            price = productxs.css('span.amount::text').extract_first()
            if not price:
                continue
            product['price'] = extract_price_eu(price)

            if productxs.select('.//div[contains(@class, "out-of-stock-label")]'):
                product['stock'] = 0
            else:
                product['stock'] = 1

            request = Request(urljoin_rfc(get_base_url(response), productxs.select('.//a/@href').extract()[0]), callback=self.parse_product, meta=response.meta)
            yield self.fetch_product(request, self.add_shipping_cost(product))

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=response.meta['product'], selector=hxs)

        loader.add_xpath('identifier', 'substring-after(//div[starts-with(@id,"product-")]/@id,"-")')
        loader.add_xpath('sku', '//*[@itemprop="sku"]/text()')
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1[@itemprop="name"]/text()')
        
        category = response.css('nav.breadcrumbs a::text').extract()[2:]
        loader.add_value('category', category)

        img = hxs.select('//a[@itemprop="image"]/img/@src').extract()
        if not img:
            img = hxs.select('//a/img[@itemprop="image"]/@src').extract()

        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        loader.add_value('brand', '')
        yield self.add_shipping_cost(loader.load_item())

    def add_shipping_cost(self, item):
        item['shipping_cost'] = 0
        return item
