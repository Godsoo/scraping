"""
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4477
"""

from scrapy import Spider, Request
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader


class VibrantDoors(Spider):
    name = 'vibrantdoors.co.uk'
    allowed_domains = ['vibrantdoors.co.uk']
    start_urls = ['http://www.vibrantdoors.co.uk/']

    def parse(self, response):
        for url in response.xpath('//div[@class="dropdown_wrap"]//a/@href').extract():
            if '/choose-your-door/' in url:
                yield Request(response.urljoin(url), callback=self.parse_category)
            if '/doors/' in url:
                yield Request(response.urljoin(url), callback=self.parse_doors)

    def parse_category(self, response):
        products = response.xpath('//ul[@class="all_doors"]//a/@href').extract()
        for url in products:
            yield Request(response.urljoin(url), callback=self.parse_item)

    def parse_item(self, response):
        url = response.xpath('//link[@rel="canonical"]/@href').extract()
        image_url = response.xpath('//a[@id="zoom1"]/@href').extract()
        image_url = response.urljoin(image_url[0])
        category = response.xpath('//p[@class="breadcrumbs"]/a[position()>1]/text()').extract()
        for product in response.xpath('//div[@class="buy_box internals"]'):
            loader = ProductLoader(item=Product(), selector=product)
            loader.add_xpath('name', 'label[@itemprop="name"]/text()[1]')
            loader.add_xpath('identifier', 'input[@name="product[]"]/@value')
            loader.add_xpath('sku', 'input[@name="product[]"]/@value')
            loader.add_xpath('price', 'label/meta[@itemprop="price"]/@content')
            loader.add_value('url', url)
            loader.add_value('image_url', image_url)
            loader.add_value('category', category)
            if not product.xpath('link[@itemprop="availability"][@href="http://schema.org/InStock"]'):
                loader.add_value('stock', 0)
            if loader.get_output_value('price') < 750:
                loader.add_value('shipping_cost', 36)
            yield loader.load_item()

    def parse_doors(self, response):
        url = response.xpath('//link[@rel="canonical"]/@href').extract()
        category = response.xpath('//p[@class="breadcrumbs"]/a[position()>1]/text()').extract()
        ids = response.xpath('//script/text()').re('ecomm_prodid.*(\[.+\])')
        ids = eval(ids[0])
        for i, product in enumerate(response.xpath('//div[@itemprop="offers"]')):
            loader = ProductLoader(item=Product(), selector=product)
            loader.add_xpath('name', './/h3[@itemprop="name"]/a/text()[1]')
            loader.add_value('identifier', ids[i])
            loader.add_value('sku', ids[i])
            loader.add_xpath('price', './/span[@itemprop="price"]/text()')
            local_url = product.xpath('.//h3[@itemprop="name"]/a/@href').extract()
            if local_url:
                local_url = response.urljoin(local_url[0])
            else:
                local_url = url
            loader.add_value('url', local_url)
            image_url = product.xpath('.//a/img/@src').extract()
            loader.add_value('image_url', response.urljoin(image_url[0]))
            loader.add_value('category', category)
            if not product.xpath('link[@itemprop="availability"][@href="http://schema.org/InStock"]'):
                loader.add_value('stock', 0)
            if loader.get_output_value('price') < 750:
                loader.add_value('shipping_cost', 36)
            yield loader.load_item()
