"""
Account: Piingu
Name: piingu-ezzence.dk
Ticket: https://app.assembla.com/spaces/competitormonitor/tickets/5001
"""


from decimal import Decimal
from scrapy.spider import Spider, Request
from scrapy.utils.url import add_or_replace_parameter
from product_spiders.utils import extract_price_eu
from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader,
)
from product_spiders.lib.schema import SpiderSchema


class EzzenceSpider(Spider):
    name = 'piingu-ezzence.dk'
    allowed_domains = ['ezzence.dk']
    start_urls = ['http://ezzence.dk/maerkeraz']

    free_shipping_over = '600'

    def parse(self, response):
        categories = response.xpath('//*[@id="maerkeraz"]/ul/li/a/@href').extract()
        for category in categories:
            yield Request(add_or_replace_parameter(category,'limit', 'all'),
                          callback=self.parse_products)

    def parse_products(self, response):
        brand_name = ''.join(response.xpath(
            '//p[contains(@class, "category-image")]/img/@title').extract())
        products = response.xpath(
            '//ul[contains(@class, "products-grid")]//*[@class="product-name"]/a/@href').extract()
        for url in products:
            yield Request(response.urljoin(url),
                          callback=self.parse_product,
                          meta={'brand': brand_name})

    def parse_product(self, response):
        schema = SpiderSchema(response)
        pdata = schema.get_product()

        is_giftcard = False

        pid = response.xpath('//input[@name="product"]/@value').extract()
        if not pid:
            return
        pid = pid[0]
        try:
            price = pdata['offers']['properties']['price']
        except:
            price = extract_price_eu(response.xpath(
                '//*[contains(@id, "product-price-")]/text()').re(r'[\d\.,]+')[0])
        try:
            out_of_stock = 'Varen er ikke' in pdata['offers']['properties']['availability']
        except:
            out_of_stock = bool(response.xpath(
                '//*[contains(@class, "availability") and contains(@class, "out-of-stock")]'))

        if pdata:
            pname = pdata['name']
        else:
            pname = ''.join(response.xpath('//*[@class="product-name"]//text()').extract()).strip()

        if 'image' in pdata:
            pimage = pdata['image']
        else:
            pimage = response.xpath('//img[@id="image"]/@src').extract()
            if not pimage:
                pimage = response.xpath('//img[contains(@class, "giftcard-img")]/@src').extract()
                if pimage:
                    is_giftcard = True
            pimage = response.urljoin(pimage[0]) if pimage else None

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('identifier', pid)
        loader.add_value('sku', pid)
        loader.add_value('url', response.url)
        loader.add_value('name',  pname)
        loader.add_value('price', price)
        loader.add_value('brand', response.meta.get('brand'))
        loader.add_value('category', response.meta.get('brand'))
        if pimage:
            loader.add_value('image_url', pimage)
        if is_giftcard or (Decimal(price) >= Decimal(self.free_shipping_over)):
            loader.add_value('shipping_cost', '0')
        else:
            loader.add_value('shipping_cost', '49.99')
        if out_of_stock:
            loader.add_value('stock', 0)

        yield loader.load_item()
