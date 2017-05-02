from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, canonicalize_url

from product_spiders.items import (Product,
        ProductLoaderWithNameStrip as ProductLoader)

class OutdoorMegastoreSpider(BaseSpider):
    name = 'outdoormegastore.co.uk'
    allowed_domains = ['outdoormegastore.co.uk']
    start_urls = ['http://www.outdoormegastore.co.uk/tents/tents-by-brand.html']
    # NOTE The site returns different layout for different user agents

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for cat in hxs.select('//a[@class="catblurblink"]'):
            yield Request(cat.select('./@href').extract()[0],
                    callback=self.parse_products,
                    meta={'brand': cat.select('./@title').extract()[0].replace('Buy ', '').replace(' Tents', '')})

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)

        for cat in hxs.select('//h2[@class="product-name"]/a/@href').extract():
            yield Request(cat, callback=self.parse_product, meta=response.meta)

        for cat in hxs.select('//a[@class="next i-next"]/@href').extract():
            yield Request(cat.replace('ajax=1&', ''), callback=self.parse_products, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), selector=hxs)

        loader.add_xpath('identifier', '//input[@name="product"]/@value')
        loader.add_xpath('sku', '//input[@name="product"]/@value')
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1/text()')
        loader.add_xpath('price', '//div[@class="product-essential"]/div[@class="product-shop"]//form//*[starts-with(@id,"product-price-")]/text()')
        loader.add_value('category', 'tents')
        img = hxs.select('//img[@id="primary"]/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        loader.add_value('brand', response.meta.get('brand'))

        if hxs.select('//button[contains(@class, "btn-cart")]'):
            loader.add_value('stock', '1')
        else:
            loader.add_value('stock', '0')
        if loader.get_output_value('price') < 50.00:
            loader.add_value('shipping_cost', '4.95')
        else:
            loader.add_value('shipping_cost', '0')
        yield loader.load_item()
