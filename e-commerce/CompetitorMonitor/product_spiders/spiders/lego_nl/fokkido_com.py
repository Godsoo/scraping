from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price_eu
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class FokkidoSpider(BaseSpider):
    name = 'fokkido.com'
    allowed_domains = ['fokkido.com']
    start_urls = ['http://www.fokkido.com/Goedkoper-LEGO-bestellen-doe-je-bij-FOKKIDO/nl/page/56/',
		  'http://www.fokkido.com/lego/']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        for cat in hxs.select('//div[contains(@class, "collection-menu")]/ul/li/a'):
            yield Request(urljoin_rfc(get_base_url(response), cat.select('./@href').extract()[0]), callback=self.parse_pages, meta={'category': cat.select('./text()').extract()[0]})

    def parse_pages(self, response):
        hxs = HtmlXPathSelector(response)

        for product in hxs.select('//div[@class="name"]//h3/a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), product), callback=self.parse_product, meta=response.meta)
        for page in hxs.select('//div[contains(@class, "collection-pagination")]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), page), callback=self.parse_pages, meta=response.meta)

    def parse_product(self, response):
        import re
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)

        loader.add_xpath('identifier', '//span[@itemprop="productID"]/text()')
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1/text()')
        loader.add_value('price', extract_price_eu(''.join(hxs.select('//span[@class="price"]//text()').extract())))
        loader.add_xpath('sku', '//*[@itemprop="sku"]/text()')
        loader.add_value('category', response.meta.get('category'))

        img = hxs.select('//div[@class="main-img"]//img/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        loader.add_value('brand', 'lego')
#        loader.add_value('shipping_cost', '0')
#        loader.add_xpath('stock', '1')
 
        yield loader.load_item()
