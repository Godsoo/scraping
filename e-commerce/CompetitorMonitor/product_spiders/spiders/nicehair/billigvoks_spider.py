import os
import urlparse

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.fuzzywuzzy import process
from product_spiders.fuzzywuzzy import fuzz

HERE = os.path.abspath(os.path.dirname(__file__))

class BilligvoksSpider(BaseSpider):
    name = 'nicehair-billigvoks.dk'
    allowed_domains = ['billigvoks.dk']
    start_urls = ['http://www.billigvoks.dk']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//td[contains(@class, "produkt_menu")]/div/table/tr/td/a')
        for category in categories:
            url = urljoin_rfc(get_base_url(response), category.select('@href').extract()[0])
            yield Request(url, callback=self.parse_products, meta={'category':category.select('text()').extract()[0],
                                                                   'brand':category.select('text()').extract()[0]})

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//div/div[@style="width: 334px; height: 151px; float: left; padding: 3px;"]')
        for product in products:
            loader = ProductLoader(item=Product(), selector=product)
            name = product.select('div/div/script/text()').extract()[1].split("underline;\'>")[1].split('</a>")')[0]
            loader.add_value('name', name)

            loader.add_value('brand', response.meta.get('brand', ''))
            loader.add_value('category', response.meta.get('category', ''))
            relative_url = product.select('div/div/script/text()').extract()[0].split("href='")[1].split("'><img")[0]
            url = urljoin_rfc(get_base_url(response), relative_url)
            loader.add_value('url', url)
            parsed = urlparse.urlparse(url)
            params = urlparse.parse_qs(parsed.query)
            identifier = params.get('Product_id')
            loader.add_value('identifier', identifier)
            image_url = product.select('div/div/script').extract()[0].split('src=')[-1].split('>')[0]
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), image_url))
            price = ''.join(product.select('div/div/span/text()').extract()).replace(',', '.')
            loader.add_value('price', price)

            if loader.get_output_value('price') > 499:
                loader.add_value('shipping_cost', '0')
            else:
                loader.add_value('shipping_cost', '35')
            yield Request(url, callback=self.parse_availability, meta={'item': loader.load_item()})

    def parse_availability(self, response):
        hxs = HtmlXPathSelector(response)
        if hxs.select(u'//font[text()="P\xe5 lager"]'):
            response.meta['item']['stock'] = '1'
            yield response.meta['item']
        else:
            self.log('OUT OF STOCK %s' % (response.meta['item']))

