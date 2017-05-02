import os

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)

HERE = os.path.abspath(os.path.dirname(__file__))


class petgoods4u_spider(BaseSpider):
    name = 'petgoods4u.co.uk'
    allowed_domains = ['petgoods4u.co.uk', 'www.petgoods4u.co.uk']
    start_urls = ('http://www.petgoods4u.co.uk/',)

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        cats = hxs.select(
            "//div[@class='categories-container']/div"
            "/div[contains(@class,'name')]/a/@href").extract()
        if cats:
            for cat in cats:
                yield Request(url=urljoin_rfc(base_url, cat))

        subcats = hxs.select(
            "//div[@class='categories-container']/div/div"
            "/div[contains(@class,'name')]/a/@href").extract()
        if subcats:
            for subcat in subcats:
                yield Request(url=urljoin_rfc(base_url, subcat))

        products = hxs.select(
            "//div[@class='products-container']"
            "//div[@class='item-name']/a/@href").extract()
        if products:
            for product in products:
                yield Request(
                    url=urljoin_rfc(base_url, product),
                    callback=self.parse_product)

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        name = hxs.select("//div[@id='content']/span/div/h1/span/text()").extract()
        price = hxs.select(
            "//div[@id='content']//div[@id='product-price']"
            "//span[@itemprop='price']/text()").extract()

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        loader.add_value('name', name)
        loader.add_value('price', price)
        yield loader.load_item()
