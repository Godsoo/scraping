import scrapy
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price
from w3lib.url import add_or_replace_parameter


class SavistoSpider(scrapy.Spider):
    name = 'andrewjames-savisto.com'
    allowed_domains = ['savisto.com']
    start_urls = ('https://www.savisto.com/kitchenware',
                  'https://www.savisto.com/gifts-and-gadgets')
    
    headers = {'Accept-Language': 'en-US,en;q=0.5'}
    
    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(url, headers=self.headers)

    def parse(self, response):
        products = response.xpath('//div[@id="products"]//a/@href').extract()
        for url in products:
            yield scrapy.Request(response.urljoin(url), callback=self.parse_product, headers=self.headers)
        next_page = response.css('.pagination').xpath('.//a[@rel="next"]/@data-val').extract_first()
        if next_page:
            next_page_url = add_or_replace_parameter(response.url, 'p', next_page)
            yield scrapy.Request(next_page_url, headers=self.headers)

    @staticmethod
    def parse_product(response):
        loader = ProductLoader(item=Product(), response=response)
        name = response.xpath('//h1[@itemprop="name"]/text()').extract_first()
        identifier = response.css('.add-to-cart ::attr(onclick)').re('AddToCart\((.+),')
        sku = response.xpath('//span[@itemprop="sku"]/text()').extract_first()
        image_url = response.css('.mainProductImage ::attr(src)').extract_first()
        price = response.xpath('//*[@itemprop="price"]/text()').extract_first()
        if not price:
            return
        price = extract_price(price)
        categories = response.xpath('//div[@class="breadcrumb"]//a/span/text()').extract()[2:-1]
        stock = response.xpath('//link[@itemprop="availability"]/@href').extract_first()
        loader.add_value('name', name)
        loader.add_value('identifier', identifier)
        loader.add_value('sku', sku)
        loader.add_value('brand', 'Savisto')
        loader.add_value('category', categories)
        loader.add_value('url', response.url)
        loader.add_value('image_url', response.urljoin(image_url))
        loader.add_value('price', price)
        if 'InStock' not in stock.strip():
            loader.add_value('stock', 0)
        yield loader.load_item()
