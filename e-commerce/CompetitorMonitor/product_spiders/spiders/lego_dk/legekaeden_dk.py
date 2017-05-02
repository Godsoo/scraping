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

class LegekaedenSpider(ProductCacheSpider):
    name = 'legekaeden.dk'
    allowed_domains = ['legekaeden.dk']
    start_urls = ('http://www.legekaeden.dk/maerker/lego/',)
    errors = []

    def retry(self, response, error="", retries=3):
        meta = response.meta.copy()
        retry = int(meta.get('retry', 0))
        if 'redirect_urls' in meta and meta['redirect_urls']:
            url = meta['redirect_urls']
        else:
            url = response.request.url
        if retry < retries:
            retry = retry + 1
            meta['retry'] = retry
            meta['recache'] = True
            return Request(url, dont_filter=True, meta=meta, callback=response.request.callback)
        else:
            self.errors.append(error)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        for productxs in hxs.select('//ul[@id="productsearchresult"]/li'):
            product = Product()
            price = productxs.select('.//div[@class="price-box"]/text()').extract().pop()
            url = urljoin_rfc(get_base_url(response), productxs.select('.//a[@class="link-product-page"]/@href').extract().pop())
            product['price'] = extract_price_eu(price)
            product['stock'] = '1'
            request = Request(url, callback=self.parse_product, meta=response.meta)
            yield self.fetch_product(request, product)

    def parse_product(self, response):
        def get_sku(name):
            sku = re.findall('[0-9]+$', name)
            if sku:
                return sku.pop()
            else:
                return ""

        hxs = HtmlXPathSelector(response)
        name = hxs.select('//h1//text()').extract()
        if not name:
            self.retry(response, "No name found on " + response.url)
            return
        name = name.pop().strip()

        identifier = hxs.select('//a[@id="mainproductquantity"]/@data-productsku').extract().pop()
        sku = get_sku(name)
        img = hxs.select('//figure[@class="product-image-main"]/img/@src').extract()

        loader = ProductLoader(item=response.meta['product'], selector=hxs)
        loader.add_value('identifier', identifier)
        loader.add_value('url', response.url)
        loader.add_value('name', name)
        loader.add_value('sku', sku)
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img.pop()))

        loader.add_value('brand', 'lego')

        yield self.add_shipping_cost(loader.load_item())

    def add_shipping_cost(self, item):
        item['shipping_cost'] = 40
        return item
