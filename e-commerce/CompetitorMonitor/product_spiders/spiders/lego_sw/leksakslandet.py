import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from scrapy.shell import inspect_response

class LeksakslandetSpider(BaseSpider):
    name = 'lego_sw-leksakslandet.se'
    allowed_domains = ['leksakslandet.se']
    start_urls = ['http://leksakslandet.se/leksaker/byggklossar-modellset/lego/']

    def parse(self, response):
        # inspect_response(response, self)
        # return
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        next_page = hxs.select('//a[contains(@class,"ty-pagination__next")]/@href').extract()
        if next_page:  # ##
            yield Request(next_page[0], callback=self.parse)

        products = hxs.select('//div[@class="grid-list"]/div//a[1]/@href').extract()
        for url in products:  # ##
            yield Request(url, callback=self.parse_product)

    def parse_product(self, response):
        # inspect_response(response, self)
        # return
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        product_loader = ProductLoader(item=Product(), selector=hxs)

        product_loader.add_value('url', response.url)

        product_name = hxs.select('//h1[@class="ty-product-block-title"]/text()').extract()[0]
        product_loader.add_value('name', product_name)

        image_url = hxs.select('//div[contains(@class,"ty-product-img")]/a/img/@src').extract()[0]
        product_loader.add_value('image_url', image_url)

        product_loader.add_xpath('identifier', '//span[contains(@id, "product_code_")]/text()')

        identifier = hxs.select('//span[@class="ty-product-feature__label" and contains(text(), "Artnr:")]/following-sibling::div[@class="ty-product-feature__value"]/text()').extract()[0]
        # product_loader.add_value('identifier', identifier)

        sku = re.search('(\d+)', identifier)
        sku = sku.group(1) if sku else ''
        product_loader.add_value('sku', sku)

        price = hxs.select('//span[@class="ty-price-num"][1]/text()').extract()[0]
        product_loader.add_value('price', price)

        category = hxs.select('//div[@class="ty-features-list"]/a/text()').extract()
        category = category[0].strip() if category else ''
        product_loader.add_value('category', category)

        product_loader.add_value('brand', 'Lego')

        yield product_loader.load_item()
