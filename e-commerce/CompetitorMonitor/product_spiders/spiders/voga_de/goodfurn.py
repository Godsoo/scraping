from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from scrapy import log

from product_spiders.utils import extract_price_eu

from datetime import datetime, timedelta


class GoodfurnSpider(BaseSpider):
    name = 'voga_de-goodfurn'
    allowed_domains = ['goodfurn.com']
    start_urls = ('http://goodfurn.com/',)

    def __init__(self, *args, **kwargs):
        super(GoodfurnSpider, self).__init__(*args, **kwargs)
        self.errors = []

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for category in hxs.select('//nav[@id="nav"]/ol/li[position()>1]//a'):
            yield Request(urljoin_rfc(get_base_url(response), category.select('./@href').extract()[0]) + '?limit=all', callback=self.parse_cat, meta={'category':category.select('./text()').extract()[0]})

    def parse_cat(self, response):
        hxs = HtmlXPathSelector(response)

        for prod in hxs.select('//div[@class="product-name"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), prod), meta=response.meta, callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1/text()')
        loader.add_xpath('sku', 'normalize-space(substring-after(//div[@class="sku"]/text(),":"))')
        loader.add_value('category', response.meta.get('category'))
        loader.add_value('price', extract_price_eu(''.join(hxs.select('//p[@class="special-price"]//span[@class="price"]/text()').extract())))
        if not loader.get_output_value('price'):
            loader.add_value('price', extract_price_eu(''.join(hxs.select('//span[@class="price"]/text()').extract())))
        loader.add_value('stock', 1)
        img = hxs.select('//div[@class="product-image-gallery"]//img/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        product = loader.load_item()
        options = hxs.select('//a[@data-productid]')
        if options:
            for o in options:
                p = Product(product)
                p['name'] += ' ' + o.select('./@title').extract()[0]
                p['identifier'] = o.select('./@data-productid').extract()[0]
                yield p
        else:
            product['identifier'] = hxs.select('//*[@data-product-id]/@data-product-id').extract()[0]
            yield product

