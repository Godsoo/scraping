from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)

from product_spiders.utils import extract_price


class RazerCompWalmartSpider(BaseSpider):
    name = 'razer_competition-walmart.com'
    allowed_domains = ['walmart.com']
    products = [{'url': 'http://www.walmart.com/ip/Logitech-G100S-Optical-Gaming-Mouse/24032207',
                 'sku': '910-003533', 'category': 'Mice', 'brand': 'Logitech'},
                {'url': 'http://www.walmart.com/ip/Logitech-G600-MMO-Gaming-Mouse/29568475',
                 'sku': '910-002864', 'category': 'Mice', 'brand': 'Logitech'},
                {'url': 'http://www.walmart.com/ip/Logitech-920-003887-G710-Plus-Mechanical-Keyboard/41441654',
                 'sku': '920-003887', 'category': 'Keyboards', 'brand': 'Logitech'},
                {'url': 'http://www.walmart.com/ip/Logitech-G930-Wireless-Gaming-Headset/15105357',
                 'sku': '981-000257', 'category': 'Audio', 'brand': 'Logitech'}]

    def start_requests(self):
        for product in self.products:
            yield Request(product['url'], meta={'product': product})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        meta = response.meta
        loader = ProductLoader(item=Product(), response=response)
        tmp = hxs.select('//form[@name="SelectProductForm"]/input[@name="product_id"]/@value').extract()
        if tmp:
            loader.add_value('identifier', tmp[0])
        else:
            loader.add_value('identifier', response.url.split('/')[-1])
        tmp = hxs.select('//h1[@itemprop="name"]/text()').extract()
        if not tmp:
            tmp = hxs.select('//h1[contains(@class,"product-name")]/text()').extract()
        if tmp:
            loader.add_value('name', tmp[0].strip())
        # image_url
        tmp = hxs.select('//div[@class="LargeItemPhoto215"]//img/@src').extract()
        if not tmp:
            tmp = hxs.select('//div[contains(@class,"product-images")][1]//img/@src').extract()
        if tmp:
            loader.add_value('image_url', tmp[0])
        # price
        tmp = hxs.select('//div[@id="WM_PRICE"]//*[contains(@class,"camelPrice")]/span/text()').extract()
        if not tmp:
            tmp = hxs.select('//div[@class="onlinePriceMP"]//*[contains(@class,"camelPrice")]/span/text()').extract()
        if not tmp:
            tmp = hxs.select('//div[@class="col5"]//div[contains(@class,"product-buying-table-row")][1]//div[contains(@class,"price-display")][1]//text()').extract()
        if tmp:
            price = extract_price(''.join(tmp).strip())
            loader.add_value('price', price)
            tmp = hxs.select('//div[@id="OnlineStat" and @class="OutOfStock"]')
            if not tmp:
                tmp = hxs.select('//p[@class="price-oos" and text()="Out of stock"]')
            if tmp:
                loader.add_value('stock', 0)
        loader.add_value('category', meta['product']['category'])
        loader.add_value('brand', meta['product']['brand'])
        loader.add_value('sku', meta['product']['sku'])
        loader.add_value('url', response.url)
        yield loader.load_item()