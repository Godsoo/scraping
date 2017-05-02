import re
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse

from product_spiders.items import Product, ProductLoader

class RichtoneMusic(BaseSpider):

    name = 'guitarguitar-richtonemusic.co.uk'
    allowed_domains = ['richtonemusic.co.uk']
    start_urls = ('http://www.richtonemusic.co.uk/',)

    def parse(self, response):
        categories = response.xpath('//div[@id="header_container_sub"]//a/@href').extract()
        categories += response.xpath('//div[@id="left_navigation"]//a/@href').extract()
        categories += response.xpath('//div[@id="right_navigation"]//a/@href').extract()
        for category in categories:
            yield Request(response.urljoin(category))

        next_page = response.xpath('//div[@id="pagination-mid-right"]/a[@title="Next"]/@href').extract()
        if next_page:
            yield Request(response.urljoin(next_page[0]))

        products = response.xpath('//div[@class="summary_description"]/a/@href').extract()
        for product in products:
            yield Request(response.urljoin(product), callback=self.parse_product)

    def parse_product(self, response):

        price = response.xpath('//h3[@itemprop="price"]/text()').extract()
        price = price[0].strip()

        name = response.xpath('//h1[@itemprop="name"]/text()').extract()[0].strip()
        brand = response.xpath('//meta[@itemprop="brand"]/@content').extract()
        brand = brand[0].strip() if brand else ''

        image_url = response.xpath('//div[@class="product-image"]/img/@src').extract()
        image_url = response.urljoin(image_url[0]) if image_url else ''

        categories = response.xpath('//p[@id="breadcrumb"]/a/text()').extract()[1:-1]

        identifier = response.xpath('//input[@name="item"]/@value').extract()
        if not identifier:
            identifier = re.findall("ecomm_prodid: '(\d+)'", response.body)

        loader = ProductLoader(response=response, item=Product())
        loader.add_value('url', response.url)
        loader.add_value('name', name)
        loader.add_value('price', price)
        loader.add_value('image_url', image_url)
        loader.add_xpath('sku', '//meta[@itemprop="sku"]/@content')
        loader.add_value('identifier', identifier[0])
        loader.add_value('brand', brand)
        loader.add_value('category', categories)
        out_of_stock = response.xpath('//div[@id="product-options"]/p[@class="sout"]')
        if out_of_stock:
            loader.add_value('stock',0)

        yield loader.load_item()

