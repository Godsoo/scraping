import scrapy
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class DecathlonSpider(scrapy.Spider):
    name = 'camelbak_fr-decathlon.fr'
    allowed_domains = ['decathlon.fr']
    start_urls = ('http://www.decathlon.fr/C-308294-camelbak',)

    def parse(self, response):
        products = response.xpath('//a[@class="product_name"]/@href ').extract()
        for url in products:
            yield scrapy.Request(response.urljoin(url), callback=self.parse_product)

    @staticmethod
    def parse_product(response):
        loader = ProductLoader(item=Product(), response=response)
        name = response.xpath('//*[@id="productName"]/text()').extract_first()
        identifier = response.xpath('//*[@id="modelId"]/@value').extract_first()
        image_url = response.xpath('//*[@id="productMainPicture"]/@src').extract_first()
        price = response.xpath('//*[@id="real_price"]/@content').extract_first()
        loader.add_value('name', name)
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        loader.add_value('brand', 'CamelBak')
        loader.add_value('url', response.url)
        loader.add_value('image_url', response.urljoin(image_url))
        loader.add_value('price', price)
        yield loader.load_item()
