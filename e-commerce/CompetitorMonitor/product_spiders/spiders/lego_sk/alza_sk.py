from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from product_spiders.items import Product, ProductLoader
from scrapy.utils.response import get_base_url
from scrapy.spider import BaseSpider
from product_spiders.utils import extract_price_eu
import re


class AlzaSkSpider(BaseSpider):
    name = 'alza.sk'
    allowed_domains = ['hracky.alza.sk']
    start_urls = ('https://hracky.alza.sk/hracky/lego/18851136.htm',)

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//div[@id="boxes"]/div//a[@class="name"]/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)
        next_page = hxs.select('//a[contains(@class, "next")]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page.pop()), callback=self.parse)

    def parse_product(self, response):
        def get_sku(name):
            res = re.findall("([0-9]{3,5}).*", name)
            if res:
                return res.pop()
            else:
                return ""

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        name = hxs.select('//h1/text()').extract().pop().strip()
        price = hxs.select('//span[@class="bigPrice"]/text()').extract().pop()
        sku = get_sku(name)

        identifier = hxs.select('//input[@id="surveyObjectId"]/@value').extract().pop()
        category = hxs.select('//div[@itemprop="breadcrumb"]/div/a[not(contains(@class, "last"))]/text()').extract()

        brand = "Lego"

        image_url = hxs.select('//img[@id="imgMain"]/@src').extract()

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_value("name", name)
        loader.add_value("identifier", identifier)
        loader.add_value("price", extract_price_eu(price))
        loader.add_value("url", response.url)

        loader.add_value("sku", sku)
        if image_url:
            loader.add_value("image_url", urljoin_rfc(base_url, image_url.pop()))
        if category:
            loader.add_value("category", category.pop())
        loader.add_value("stock", 1)
        loader.add_value("brand", brand)
        loader.add_value('shipping_cost', 5.75)
        yield loader.load_item()
