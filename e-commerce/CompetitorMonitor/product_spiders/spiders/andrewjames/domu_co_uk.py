import scrapy
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price


class DomuSpider(scrapy.Spider):
    name = 'andrewjames-domu.co.uk'
    allowed_domains = ['domu.co.uk']
    start_urls = ('http://www.domu.co.uk/catalogsearch/result/index?limit=all&q=Vonshef',)

    def parse(self, response):
        products = response.xpath('//div[@class="col-1-4 pod"]/a/@href').extract()
        for url in products:
            yield scrapy.Request(response.urljoin(url), callback=self.parse_product)

    @staticmethod
    def parse_product(response):
        loader = ProductLoader(item=Product(), response=response)
        name = response.xpath('//*[@id="product-page"]//h1[@itemprop="name"]/text()').extract_first()
        identifier = response.xpath('//input[@name="product"]/@value').extract_first()
        image_url = response.xpath('//*[@id="main-product-image"]/@src').extract_first()
        price = response.xpath('//div[@itemprop="price"]/span[@class="price"]/text()').extract_first()
        if not price:
            return
        price = extract_price(price)
        stock = response.xpath('//div[@itemprop="availability"]/text()').extract_first()
        loader.add_value('name', name)
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        loader.add_value('brand', 'Vonshef')
        loader.add_value('url', response.url)
        loader.add_value('image_url', response.urljoin(image_url))
        loader.add_value('price', price)
        if price < 40:
            loader.add_value('shipping_cost', 2.99)
        if stock != 'in stock':
            loader.add_value('stock', 0)
        yield loader.load_item()
