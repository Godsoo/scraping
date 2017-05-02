from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price_eu as extract_price
import re


class EbrixSeSpider(BaseSpider):
    name = 'ebrix.se'
    allowed_domains = ['ebrix.se']
    start_urls = ('http://ebrix.se/',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # parse categories
        urls = response.css('.listmenu a::attr(href)').extract()
        for url in urls:
            yield Request(response.urljoin(url), callback=self.parse_product_list)

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # parse categories
        urls = hxs.select('//div[@class="grupprutor"]//li//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product_list)

        products = response.css('.product-item')
        for product in products:
            product_loader = ProductLoader(item=Product(), selector=product)
            name = product.select('.//h3/text()').extract_first()
            product_loader.add_value('name', name)
            sku = ''
            for match in re.finditer(r"([\d,\.]+)", name):
                if len(match.group()) > len(sku):
                    sku = match.group()
            product_loader.add_value('sku', sku)
            image_url = product.select('.//img[@itemprop="image"]/@src').extract_first()
            product_loader.add_value('image_url', response.urljoin(image_url))
            price = product.xpath('.//span[@itemprop="price"]/text()').extract_first()
            if not price:
                price = product.select('.//div[@class="txt"]//span/text()').extract_first()

            product_loader.add_value('price', extract_price(''.join(price.split())))
            product_loader.add_value('shipping_cost', '49')

            stock = 'InStock' in product.xpath('.//link[@itemprop="availability"]/@href').extract_first()
            product_loader.add_value('stock', int(stock))
            product_loader.add_xpath('identifier', '@data-productid')
            url = product.xpath('.//a/@href').extract_first()
            product_loader.add_value('url', response.urljoin(url))
            item = product_loader.load_item()
            yield Request(item['url'], callback=self.parse_product, meta={'item': item})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        item = response.meta['item']

        name = response.xpath('//h1[@itemprop="name"]')
        if name:
            yield item
