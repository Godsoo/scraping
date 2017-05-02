import scrapy
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class FahrradSpider(scrapy.Spider):
    name = 'camelbak_de-fahrrad.de'
    allowed_domains = ['fahrrad.de']
    start_urls = ('http://www.fahrrad.de/camelbak.html?page=0',)

    def parse(self, response):
        products = response.xpath('//a[@class="productLink"]/@href').extract()
        for url in products:
            yield scrapy.Request(response.urljoin(url), callback=self.parse_product)
        pages = response.xpath('//div[@class="productPages"]//a/@href').extract()
        for url in pages:
            yield scrapy.Request(response.urljoin(url), callback=self.parse)

    @staticmethod
    def parse_product(response):
        loader = ProductLoader(item=Product(), response=response)
        name = response.xpath('//*[@id="ProductsInfo"]/h1/text()').extract_first()
        identifier = response.xpath('//*[@id="productOptions"]/@data-productid').extract_first()
        image_url = response.xpath('//img[@class="mainImage"]/@src').extract_first()
        price = response.xpath('//meta[@itemprop="price"]/@content').extract_first()
        stock = response.xpath('//meta[@itemprop="availability"]/@content').extract_first()
        loader.add_value('name', name)
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        loader.add_value('brand', 'CamelBak')
        loader.add_value('url', response.url)
        loader.add_value('image_url', image_url)
        loader.add_value('price', price)
        if stock != 'in_stock':
            loader.add_value('stock', 0)
        yield loader.load_item()
