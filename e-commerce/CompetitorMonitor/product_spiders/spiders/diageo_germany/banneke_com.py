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

class BannekeSpider(ProductCacheSpider):
    name = 'banneke.com'
    allowed_domains = ['banneke.com']
    start_urls = ('http://banneke.com',)

    def _start_requests(self):
        yield Request('http://www.banneke.com/Whisky/Whiskey/International/Amrut_Malt_Whisky_aus_Indien_46_0.70', callback=self.parse_product, meta={'product': Product()})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for cat in hxs.select('//a[contains(@class,"menu2")]/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), cat), callback=self.parse_cat)

    def parse_cat(self, response):
        hxs = HtmlXPathSelector(response)

        for productxs in hxs.select('//li[@class="product"]'):
            product = Product()
            product['price'] = extract_price_eu(''.join(productxs.select('.//div/span[@class="price"]//text()').extract()))
            product['stock'] = '1'

            request = Request(urljoin_rfc(get_base_url(response), productxs.select('.//h2[@class="title"]/a/@href').extract()[0]), callback=self.parse_product, meta=response.meta)
            yield self.fetch_product(request, self.add_shipping_cost(product))

        for page in hxs.select('//div[@class="navigation"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), page), callback=self.parse_cat)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=response.meta['product'], selector=hxs)
        # this field changes a lot
        # loader.add_xpath('identifier', '//input[@name="product"]/@value')
        loader.add_value('identifier', ''.join(hxs.select('//td[contains(text(),"Art.-Nr.:")]/text()').extract()).split(':')[-1].strip())
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//div[@class="info"]//*[@itemprop="name"]//text()')
        loader.add_value('sku', ''.join(hxs.select('//td[contains(text(),"Art.-Nr.:")]/text()').extract()).split(':')[-1].strip())

        loader.add_xpath('category', '//li[contains(@class,"menu1active")]//a/text()[1]')

        img = hxs.select('//img[@itemprop="image"]/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        loader.add_xpath('brand', '//div[@id="product_content_3"]//h1/text()')
        yield self.add_shipping_cost(loader.load_item())

    def add_shipping_cost(self, item):
        if item.get('price', 0) < 95:
            item['shipping_cost'] = 3.90
        else:
            item['shipping_cost'] = 0

        return item
