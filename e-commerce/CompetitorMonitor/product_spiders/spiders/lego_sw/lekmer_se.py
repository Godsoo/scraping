from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price_eu as extract_price


class LekmerSeSpider(BaseSpider):
    name = 'lekmer.se'
    allowed_domains = ['lekmer.se']
    start_urls = ('http://lekmer.se/lego/',)
    
    def parse(self, response):
        for url in response.css('.section-body a::attr(href)').extract():
            yield Request(response.urljoin(url), self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # parse products list
        urls = response.css('.product-card-link').xpath('@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)
        # parse pagination
        urls = response.css('.js-pagination').xpath('.//@data-link').extract()
        for url in urls:
            yield Request(response.urljoin(url), callback=self.parse_category)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_name = hxs.select('//h1[@itemprop="name"]/text()').extract_first()
        image_url = response.css('.js-main-image').xpath('@src').extract_first()
        product_loader.add_value('image_url', response.urljoin(image_url))
        product_loader.add_value('name', product_name)
        product_loader.add_value('url', response.url)
        identifier = hxs.select('//input[@name="id"]/@value').extract_first()
        product_loader.add_value('identifier', identifier)
        sku = response.css('.js-product-info').xpath('@data-product').re('"erpId":.+"(.+)"')
        sku = sku[0] if sku else ''
        product_loader.add_value('sku', sku)
        price = response.css('.js-product-info').xpath('@data-product').re('"priceCurrent":(.+),')
        price = price[0] if price else ''
        product_loader.add_value('price', price)
        if product_loader.get_collected_values('price') and product_loader.get_collected_values('price')[0] < 1000:
            product_loader.add_value('shipping_cost', '49')
        out_of_stock = hxs.select('//form[@id="block-monitor-product-form"]')
        if out_of_stock:
            product_loader.add_value('stock', 0)
        product = product_loader.load_item()
        yield product
