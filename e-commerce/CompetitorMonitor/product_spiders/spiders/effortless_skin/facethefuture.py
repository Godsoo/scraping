import logging
import re

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoader
from product_spiders.base_spiders.primary_spider import PrimarySpider


class FaceTheFutureSpider(PrimarySpider):
    name = "www.facethefuture.co.uk"
    allowed_domains = ["www.facethefuture.co.uk"]
    start_urls = (
        "http://www.facethefuture.co.uk/shop/shop-by-brand/",
    )
    errors = []

    products_parsed = []

    csv_file = 'facethefuture_crawl.csv'

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        categories = hxs.select('//ul[contains(@class,"sf-menu")]/li/a/@href').extract()
        for url in categories:
            yield Request(url)

        brands = hxs.select('//div[@id="subcategories"]/ul/li/h5/a/@href').extract()
        for url in brands:
            yield Request(url, callback=self.parse_listing)

    def parse_listing(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        subcategories = hxs.select('//div[@id="subcategories"]/ul/li/h5/a/@href').extract()
        for url in subcategories:
            yield Request(url, callback=self.parse_listing)

        links = hxs.select('//ul[contains(@class, "product_list")]/li/div/div[2]/h5/a/@href').extract()
        for link in links:
            yield Request(link, callback=self.parse_product)

        next_page = hxs.select('//ul[@class="pagination"]/li[@id="pagination_next_bottom"]/a/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page.pop()), callback=self.parse_listing)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        name = hxs.select('//h1[@itemprop="name"]/text()').extract().pop()
        identifier = hxs.select('//input[@name="id_product"]/@value').extract().pop()
        sku = hxs.select('//span[@itemprop="sku"]/text()').extract()
        if not sku:
            sku = re.search("productReference='(.*?)\';", response.body)
            sku = sku.group(1).lower() if sku else ''
        else:
            sku = sku.pop().lower()

        price = hxs.select('//span[@itemprop="price"]/text()').extract()
        if not price:
            price = '0.0'
        stock = hxs.select('//span[@id="availability_value"]/text()').extract()
        if stock and "in stock" in stock.pop().lower():
            stock = 1
        else:
            stock = 0
        category = hxs.select('//div[contains(@class, "breadcrumb")]/a/text()').extract().pop()
        brand = hxs.select('//div[contains(@class, "breadcrumb")]/a/text()').extract()[1]
        image_url = hxs.select('//div[@id="image-block"]//img/@src').extract()

        loader = ProductLoader(response=response, item=Product())
        loader.add_value('name', name)
        loader.add_value('price', price)
        loader.add_value('url', response.url)
        loader.add_value('identifier', identifier)
        if sku:
            loader.add_value('sku', sku)
        if stock:
            loader.add_value('stock', '1')
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url.pop()))
        if category:
            loader.add_value('category', category)
        if 'CLEARANCE' not in brand:
            loader.add_value('brand', brand)
        else:
            loader.add_value('category', "Clearance products")
        loader.add_value('shipping_cost', 'N/A')

        item = loader.load_item()
        yield item
