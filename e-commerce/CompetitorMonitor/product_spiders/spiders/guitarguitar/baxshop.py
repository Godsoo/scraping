from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse

from product_spiders.items import Product, ProductLoader

class BaxShopSpider(BaseSpider):

    name = 'guitarguitar-bax-shop.co.uk'
    allowed_domains = ['bax-shop.co.uk']
    start_urls = ('https://www.bax-shop.co.uk/',)

    def parse(self, response):
        categories = response.xpath('//div[@class="header-bar-menu"]//a/@href').extract()
        categories += response.xpath('//nav[@class="nav menu"]//a/@href').extract()
        categories += response.xpath('//nav[@class="nav category"]//a/@href').extract()
        categories += response.xpath('//div[contains(@class, "category")]/a/@href').extract()
        categories += response.xpath('//div[@data-name="filters[brand]"]//a/@href').extract()
        for category in categories:
            if 'products/discontinued' in category:
                continue
            yield Request(response.urljoin(category))

        next_page = response.xpath('//div[@class="pagination"]//span[contains(@class, "next")]/a/@href').extract()
        if next_page:
            if 'products/discontinued' not in next_page[0]:
                yield Request(response.urljoin(next_page[0]))

        products = response.xpath('//div[@class="product-name"]//a/@href').extract()
        for product in products:
            yield Request(response.urljoin(product), callback=self.parse_product)

    def parse_product(self, response):

        price = response.xpath('//meta[@itemprop="price"]/@content').extract()
        price = price[0].strip()

        name = response.xpath('//h1[@itemprop="name"]/text()').extract()[0].strip()
        brand = response.xpath('//span[@itemprop="brand"]//span[@itemprop="name"]/text()').extract()
        brand = brand[0].strip() if brand else ''

        identifier = response.xpath('//div[@class="productbox"]//input[@name="productId"]/@value').extract()[0]

        categories = response.xpath('//div[@id="myPathway"]/span/a[not(@class="hidden")]/span/text()').extract()[2:]
        if len(categories)>2:
            categories = categories[:3]

        loader = ProductLoader(response=response, item=Product())
        loader.add_value('url', response.url)
        loader.add_value('name', name)
        loader.add_value('price', price)
        loader.add_xpath('image_url', '//img[@id="zoom-image"]/@src')
        loader.add_xpath('sku', '//span[@itemprop="sku"]/text()')
        loader.add_value('identifier', identifier)
        loader.add_value('brand', brand)
        loader.add_value('category', categories)
        stock = response.xpath('//div[@class="row orderbox product schema"]//div[@class="productstock"]/span[contains(@class, "state-instock")]').extract()
        if not stock:
            loader.add_value('stock',0)

        yield loader.load_item()

