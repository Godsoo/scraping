import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price_eu as extract_price


class Warehouse19Spider(BaseSpider):
    name = 'lego_sw-warehouse19.se'
    allowed_domains = ['warehouse19.se']
    start_urls = ('http://warehouse19.se/lego-minifig-parts/',
                  'http://warehouse19.se/lego-minifigs/',
                  'http://warehouse19.se/lego-set/',
                  'http://warehouse19.se/lego-custom-set/',
                  'http://warehouse19.se/lego-bricks/')

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//ul[contains(@class, "grid-gallery--categories")]//a/@href').extract()
        for url in categories:
            yield Request(urljoin_rfc(base_url, url))

        # next_page = hxs.select('').extract()
        next_page = None
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]))

        products = hxs.select('//ul[contains(@class, "grid-gallery--products")]//a[@itemprop="url"]/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        product_loader = ProductLoader(item=Product(), selector=hxs)

        product_loader.add_value('url', response.url)

        product_name = hxs.select('//h1[@class="product-title"]/text()').extract()[0]
        product_loader.add_value('name', product_name)

        image_url = hxs.select('//img[@itemprop="image"]/@src').extract()
        if image_url:
            product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))

        identifier = hxs.select('//span[@id="articleno"]/text()').extract()[0]
        product_loader.add_value('identifier', identifier)

        sku = re.search('(\d+)', identifier)
        sku = sku.group(1) if sku else ''
        if not sku:
            sku = re.search('(\d{3,})', product_name)
            sku = sku.group(1) if sku else ''
        product_loader.add_value('sku', sku)

        price = hxs.select('//span[@itemprop="price"]/text()').extract()[0]
        product_loader.add_value('price', extract_price(price))

        category = hxs.select('//ol[@itemprop="breadcrumb"]/li/a/text()').extract()
        category = category[-1].strip() if category else ''
        product_loader.add_value('category', category)

        product_loader.add_value('brand', 'Lego')

        yield product_loader.load_item()
