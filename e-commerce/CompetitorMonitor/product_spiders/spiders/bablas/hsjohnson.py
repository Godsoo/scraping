import re

from scrapy import Spider
from scrapy.http import Request

from product_spiders.items import Product
from bablas_item import ProductLoader


class WatchShopSpider(Spider):
    name = 'bablas-hsjohnson.com'
    allowed_domains = ['hsjohnson.com']
    start_urls = ('https://www.hsjohnson.com/currency/GBP/watches-c123',
                  'https://www.hsjohnson.com/currency/GBP/clocks-barometers-c122')

    def parse(self, response):

        product_urls = response.xpath('//div[@class="product__details__title"]/a/@href').extract()
        for url in product_urls:
            yield Request(response.urljoin(url), callback=self.parse_product)

        next_page = response.xpath('//a[contains(@class, "next-page")]/@href').extract()
        if next_page:
            url = response.urljoin(next_page[0])
            yield Request(url)

    def parse_product(self, response):

        identifier = response.xpath('//input[@name="parent_product_id"]/@value').extract()
        loader = ProductLoader(item=Product(), response=response)

        sku = response.xpath('//span[@id="js-product-reference"]/text()').extract()
        sku = sku[0].strip() if sku else ''

        category = response.xpath('//div[contains(@class, "breadcrumb")]//li//span/text()').extract()[1:-1]
        loader.add_value('identifier', identifier)
        name = response.xpath('//h1[@itemprop="name"]//span/text()').extract()
        name = ' '.join(map(lambda x: x.strip(), name))
        loader.add_value('name', name)
        brand = response.xpath('//span[@class="product-content__title--brand"]/text()').extract()[0].strip()
        loader.add_value('brand', brand)
        loader.add_value('category', category)
        loader.add_value('sku', sku)
        loader.add_value('identifier', identifier)
        loader.add_value('url', response.url)
        price = response.xpath('//span[@itemprop="price"]/@content').extract()
        loader.add_value('price', price)
        image_url = response.xpath('//a[contains(@class, "product__image__zoom-link")]/@href').extract()
        image_url = response.urljoin(image_url[0]) if image_url else ''
        loader.add_value('image_url', image_url)
        # if out of stock the 'in stock' message has style="display:none", out of stock message is visible
        # there isn't a style attribute
        out_of_stock = response.xpath('//span[@id="js-product-stock-message-out-of-stock" and not(@style)]')
        if out_of_stock:
            loader.add_value('stock', 0)
        yield loader.load_item()
