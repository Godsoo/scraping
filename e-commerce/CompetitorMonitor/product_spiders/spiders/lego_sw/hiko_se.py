from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price


class HikoSeSpider(BaseSpider):
    name = 'hiko.se'
    allowed_domains = ['hiko.se']
    start_urls = ('http://www.hiko.se/Leksaker/LEGO',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        #parse categories
        urls = hxs.select('//div[@class="item-list"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product_list)

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        urls = hxs.select('//div[@class="item-list"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)
        #parse pagination
        urls = hxs.select('//div[@class="pagination"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product_list)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        product_loader = ProductLoader(item=Product(), selector=hxs)
        price = hxs.select('//span[@itemprop="price"]/text()').extract()[0].strip()
        product_loader.add_value('price', price)
        product_loader.add_value('category', hxs.select('//ul[contains(@class, "breadcrumbs")]/li/a/text()').extract()[-2])      
        product_loader.add_value('url', response.url)
        product_loader.add_xpath('image_url', '//div[@id="image-0"]/img[1]/@src')
        product_loader.add_xpath('name', '//h1[@itemprop="name"]/text()')
        product_loader.add_value('shipping_cost', '49')
        identifier = response.xpath('//input[@id="ProductId"]/@value').extract()
        if not identifier:
            identifier = response.xpath('//form/@action').re("/Cart/Add/(\d+)")
            if not identifier:
                return
        else:
            product_loader.add_value('stock', 0)
        product_loader.add_value('identifier', identifier[0])
        sku = hxs.select('//div[@class="art-nr"]/text()').re('Art.nr: *(.+)')
        sku = sku[0] if sku else ''
        product_loader.add_value('sku', sku)
        product = product_loader.load_item()
        yield product
