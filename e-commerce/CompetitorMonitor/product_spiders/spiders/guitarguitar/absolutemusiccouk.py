from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse

from product_spiders.items import Product, ProductLoader

class AbsolutemusicCoUk(BaseSpider):

    name = 'guitarguitar-absolutemusic.co.uk'
    allowed_domains = ['absolutemusic.co.uk', 'www.absolutemusic.co.uk']
    start_urls = ('https://www.absolutemusic.co.uk',)

    def parse(self, response):
        categories = response.xpath('//nav[@class="catagories-navigation"]//ul[@class="mega-menu-links"]//li/a/@href').extract()
        for category in categories:
            yield Request(response.urljoin(category), callback=self.parse_cat)

    def parse_cat(self, response):

        next_page = response.xpath('//ul[@class="page-numbers"]//a[@title="Next"]/@href').extract()
        if next_page:
            yield Request(next_page[0], callback=self.parse_cat)

        products = response.xpath('//ul[@id="products-list"]/li[contains(@class,"product")]/div[@class="product-img"]//a/@href').extract()
        products += response.xpath('//a[@class="product-title"]/@href').extract()

        categories = response.xpath('//div[@class="breadcrumbs"]//li/a/text()').extract()
        categories += response.xpath('//div[@class="breadcrumbs"]//li/strong/text()').extract()
        categories = categories[1:] if categories else ''
        for product in products:
            yield Request(product, callback=self.parse_product, meta={'categories': categories})

    def parse_product(self, response):

        price = response.xpath('//div[@id="product-info-panel-inner"]//p[@class="special-price"]/span[@class="price"]/text()').extract()
        if not price:
            price = response.xpath('//div[@id="product-info-panel-inner"]//span[@class="regular-price"]/span[@class="price"]/text()').extract()
        price = price[0].strip() if price else '0'

        name = response.xpath('//h1[@itemprop="name"]/text()').extract()[0].strip()
        brand = response.xpath('//tr[th[contains(text(), "Brand")]]/td/text()').extract()
        brand = brand[0].strip() if brand else ''

        loader = ProductLoader(response=response, item=Product())
        loader.add_value('url', response.url)
        loader.add_value('name', name)
        loader.add_value('price', price)
        loader.add_xpath('image_url', '//img[@id="image"]/@src')
        loader.add_xpath('sku', '//span[@itemprop="productID"]/text()')
        loader.add_xpath('identifier', '//input[@name="product"]/@value')
        loader.add_value('brand', brand)
        loader.add_value('category', response.meta['categories'])
        stock = response.xpath('//a[@class="availability in-stock"]')
        if not stock:
            loader.add_value('stock',0)

        yield loader.load_item()

