import scrapy
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class FuturumshopSpider(scrapy.Spider):
    name = 'camelbak_nl-futurumshop.nl'
    allowed_domains = ['futurumshop.nl']
    start_urls = ('http://www.futurumshop.nl/zoeken/v_camelbak&collection=true',)

    def parse(self, response):
        products = response.xpath('//div[@class="col-xs-12 col-sm-6 col-md-3 productImage"]/a/@href').extract()
        for url in products:
            yield scrapy.Request(response.urljoin(url), callback=self.parse_product)

        pages = response.xpath('//div[@class="paging"]//a/@href').extract()
        for url in pages:
            yield scrapy.Request(response.urljoin(url), callback=self.parse)

    @staticmethod
    def parse_product(response):
        loader = ProductLoader(item=Product(), response=response)
        name = response.xpath('//h1[@itemprop="name"]/text()').extract_first()
        identifier = response.xpath('//input[@name="product"]/@value').extract_first()
        image_url = response.xpath('//div[@class="productImage hidden-xs"]/@data-imagelarge').extract_first()
        price = response.xpath('//p[@class="newPrice"]/text()').extract_first()
        loader.add_value('name', name)
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        loader.add_value('brand', 'CamelBak')
        loader.add_value('url', response.url)
        loader.add_value('image_url', response.urljoin(image_url))
        loader.add_value('price', price)
        yield loader.load_item()
