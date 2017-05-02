import re

from scrapy import Spider
from scrapy.http import Request

from product_spiders.items import Product
from bablas_item import ProductLoader


class BritishWatchCompany(Spider):
    name = 'bablas-britishwatchcompany.com'
    allowed_domains = ['britishwatchcompany.com']
    start_urls = ('http://www.britishwatchcompany.com/watches-c104',)

    def parse(self, response):
        product_urls = response.xpath('//a[@class="product_title"]/@href').extract()
        for url in product_urls:
            yield Request(response.urljoin(url), callback=self.parse_product)

        next_page = response.xpath('//a[contains(@class, "next_page")]/@href').extract()
        if next_page:
            url = response.urljoin(next_page[0])
            yield Request(url)

    def parse_product(self, response):
        identifier = response.xpath('//input[@id="parent_product_id"]/@value').extract()
        loader = ProductLoader(item=Product(), response=response)

        sku = response.xpath('//span[@id="product_reference"]/text()').extract()
        sku = sku[0].strip() if sku else ''

        category = response.xpath('//div[@id="breadcrumb_container"]//a/text()').extract()[1:]
        loader.add_value('identifier', identifier)
        name = response.xpath('//span[@id="product_title"]/text()').extract()
        loader.add_value('name', name)
        brand = response.xpath('//meta/@data-brand').extract()
        brand = brand[0].replace('Watches', '').strip() if brand else ''
        loader.add_value('brand', brand)
        loader.add_value('category', category)
        loader.add_value('sku', sku)
        loader.add_value('identifier', identifier)
        loader.add_value('url', response.url)
        price = response.xpath('//span[@itemprop="price"]/@content').extract()
        loader.add_value('price', price)
        image_url = response.xpath('//img[@id="product_medium_image"]/@src').extract()
        image_url = response.urljoin(image_url[0]) if image_url else ''
        loader.add_value('image_url', image_url)
        # if out of stock the 'in stock' message has style="display:none", out of stock message is visible
        # there isn't a style attribute
        out_of_stock = response.xpath('//span[@class="product_out_stock" and not(@style)]')
        if out_of_stock:
            loader.add_value('stock', 0)
        if loader.get_output_value('price') < 50:
            loader.add_value('shipping_cost', 3.50)
        yield loader.load_item()
