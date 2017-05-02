import os
import re
import json

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from scrapy.spider import BaseSpider
from urlparse import urlparse
from urlparse import parse_qs
from urllib import  urlencode



def set_parameter(url, data):
    url_withoutqs = url.split('?')[0]
    qs = parse_qs(urlparse(url).query)
    for key, val in data.items():
        qs[key] = val
    qs = urlencode(qs)
    return "%s?%s" % (url_withoutqs, qs)



class FutureShopSpider(BaseSpider):
    name = 'futureshop.ca'
    allowed_domains = ['competitormonitor.com', 'www.bestbuy.ca', 'api.bestbuy.ca']
    website_id = 476871

    start_urls = (
        'http://www.bestbuy.ca/Search/SearchResults.aspx?query=musical+instruments&lang=en-CA',
    )

    root_path = os.path.abspath(os.path.dirname(__file__))

    new_system = True
    old_system = False

    handle_httpstatus_list = [500]

    def parse(self, response):
        if 'redirect_urls' in response.meta:
            url = response.meta['redirect_urls'][0]
            rc = response.meta.get('retries_count', 0)
            rc += 1
            if rc > 20:
                self.log('Redirect retry max count reached, giving up: {}'.format(url))
            else:
                self.log('Redirected, trying again: #{}'.format(rc))
                yield Request(url, dont_filter=True, meta={'retries_count': rc})
            return
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        subcategories = hxs.select('//ul[@class="category-list clearfix"]//a/@href').extract()
        for subcat in subcategories:
            yield Request(urljoin_rfc(base_url, set_parameter(response.url, {"query": subcat})), meta=response.meta)
        next_page = hxs.select('//a[@data-page]/@href').extract()
        for url in next_page:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse)

        products = hxs.select('//h4[@class="prod-title"]/a/@href').extract()
        for product in products:
            yield Request(urljoin_rfc(base_url, product), meta=response.meta, callback=self.parse_product)

    def parse_product(self, response):
        if 'redirect_urls' in response.meta:
            url = response.meta['redirect_urls'][0]
            rc = response.meta.get('retries_count', 0)
            rc += 1
            if rc > 20:
                self.log('Redirect retry max count reached, giving up: {}'.format(url))
            else:
                self.log('Redirected, trying again: #{}'.format(rc))
                yield Request(url, dont_filter=True, meta={'retries_count': rc})
            return
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        name = hxs.select('//h1[@class="product-title"]/span/text()').extract()[0].strip()
        identifier = hxs.select('//span[@itemprop="productid"]/text()').extract()[0].strip()
        sku = hxs.select('//span[@itemprop="model"]/text()').extract()
        categories = hxs.select('//span[@class="breadcrumb"]/span/a/text()').extract()[1:]
        price = hxs.select('//div[@itemprop="price"]/span[@class="amount"]/text()').extract()[0]
        brand = hxs.select('//span[@class="brand-logo"]/img/@alt').extract()
        image_url = hxs.select('//div[@id="pdp-gallery"]/img/@src').extract()

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_value('name', name)
        loader.add_value('url', response.url)
        loader.add_value('identifier', identifier)
        loader.add_value('price', price)
        loader.add_value('category', categories)
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        if sku:
            loader.add_value('sku', sku[0].strip())
        if brand:
            loader.add_value('brand', brand[0].strip())
        # out_of_stock = hxs.select('//span[@itemprop="availability"]/span[contains(text(), "Sold Out")]')
        # if out_of_stock:
        #     loader.add_value('stock', 0)
        product = loader.load_item()
        yield product
        #stock_url = 'http://api.bestbuy.ca/availability/products?callback=apiAvailability&accept-language=en&skus=%s' % identifier
        #yield Request(stock_url, meta={'product': product}, callback=self.parse_stock)

    # def parse_stock(self, response):
    #     product = response.meta.get('product', Product())
    #     data = json.loads(re.findall('apiAvailability\((.*)\)', response.body)[0])
    #     if data['availabilities'][0]['shipping']['status'].lower() == 'instock':
    #         product['stock'] = 1
    #     else:
    #         product['stock'] = 0
    #     yield product
