from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from product_spiders.items import Product, ProductLoader
from scrapy.utils.response import get_base_url
from scrapy.spider import BaseSpider
from product_spiders.utils import extract_price


class FitflopSpider(BaseSpider):
    name = 'fitflop.co.uk'
    allowed_domains = ['fitflop.co.uk', 'fitflop.eu']
    start_urls = ('http://www.fitflop.co.uk',)

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//li[@class="rootclass"]/ul/li/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_category)

    def parse_category(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        # Products
        for url in hxs.select('//div[contains(@class, "producttile")]/div[@class="name"]/a/@href').extract():
            url = url.split("?")[0]
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)
        # Pages
        for url in hxs.select('//div[@class="pagination"][1]/ul/li[not(contains(@class, "viewall"))]/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_category)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        name = hxs.select('//h1/text()').extract().pop().strip()
        price = extract_price(hxs.select('//form/div/div/div[@class="price"]/h2[@class="salesprice"]/span[@itemprop="price"]/text()').extract().pop())
        sku = hxs.select('//span[@itemprop="sku"]/text()').extract().pop()
        identifier = hxs.select('//input[contains(@class, " productid")]/@value').extract().pop()

        brand = hxs.select('//input[contains(@class, "productbrand")]/@value').extract()

        image_url = hxs.select('//div[@class="productimage"]/img/@src').extract()

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_value("name", name)
        loader.add_value("identifier", identifier)
        loader.add_value("price", price)
        loader.add_value("url", response.url)

        loader.add_value("sku", sku)
        if image_url:
            loader.add_value("image_url", urljoin_rfc(base_url, image_url.pop()))
        loader.add_value("stock", 1)
        if brand:
            loader.add_value("brand", brand.pop())
        yield loader.load_item()
