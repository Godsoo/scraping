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

class CookSpider(ProductCacheSpider):
    name = 'coop.dk'
    allowed_domains = ['coop.dk']
    start_urls = ('https://webshop.coop.dk/kategori/boern/legetoej/lego-shop',)

    def _start_requests(self):
        yield Request('https://webshop.coop.dk/vare/lego-lord-of-the-rings-gandalf-ankommer-9469/5702014837539?kategorier=boern%2Flegetoej%2Flego-shop%2Flord-of-the-rings', callback=self.parse_product)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        # skip age categories
        for cat in hxs.select('//div[@class="fagbutik-kategoribilledeblok-container"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), cat), callback=self.parse_list)

    def parse_list(self, response):
        hxs = HtmlXPathSelector(response)

        for productxs in hxs.select('//ul[contains(@class, "product_list")]/li'):
            product = Product()
            product['price'] = extract_price_eu(''.join(productxs.select('.//p[@class="memberprice"]//text()').extract()))
            if productxs.select('.//input[contains(@class,"green")]'):
                product['stock'] = '1'
            else:
                product['stock'] = '0'

            request = Request(urljoin_rfc(get_base_url(response), productxs.select('.//a/img/../@href').extract()[0]), callback=self.parse_product, meta=response.meta)
            yield self.fetch_product(request, self.add_shipping_cost(product))

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=response.meta['product'], selector=hxs)

        loader.add_value('identifier', response.url.split('/')[-1].split('?')[0])
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1/text()')
        sku = ''.join(hxs.select('//div[@id="product-heading"]/p/text()').extract())
        try:
            loader.add_value('sku', re.search('(\d{3}\d*)', sku).groups()[0])
        except:
            self.log('No SKU for %s' % (response.url))
        loader.add_xpath('category', '//nav[@class="breadcrumb"]/a[position()=last()]//text()')

        img = hxs.select('//div[@class="image"]//img/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        loader.add_value('brand', 'lego')
        yield self.add_shipping_cost(loader.load_item())

    def add_shipping_cost(self, item):
        if item['price'] >= 400:
            item['shipping_cost'] = 0
        else:
            item['shipping_cost'] = 49
        return item
