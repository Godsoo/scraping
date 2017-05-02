from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from product_spiders.items import Product, ProductLoader
from scrapy.utils.response import get_base_url
from scrapy.spider import BaseSpider
from product_spiders.utils import extract_price_eu
import re


class MallSkSpider(BaseSpider):
    name = 'mall.sk'
    allowed_domains = ['mall.sk']
    start_urls = ('http://www.mall.sk/lego/',)

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        for url in hxs.select('//li[@class="active"]/ul/li/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_category)

    def parse_category(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        for url in hxs.select('//ul[contains(@class, "p-list")]/li/h3/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)
        next_page = hxs.select('//a[@class="next"]/@href').extract()
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

        name = hxs.select('//div[@id="content"]/h1/text()').extract().pop().strip()
        price = extract_price_eu(hxs.select('//div[@id="content"]//b[@id="se_price"]/text()').extract().pop())
        sku = get_sku(name)

        identifier = hxs.select('//div[@id="text-box"]//input[@name="variant_id"]/@value').extract().pop()
        category = hxs.select('//p[@id="crumbs"]//a/text()').extract()

        brand = "Lego"

        image_url = hxs.select('//p[@id="master"]//img/@src').extract()

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_value("name", name)
        loader.add_value("identifier", identifier)
        loader.add_value("price", price)
        loader.add_value("url", response.url)

        loader.add_value("sku", sku)
        if image_url:
            loader.add_value("image_url", urljoin_rfc(base_url, image_url.pop()))
        if category:
            loader.add_value("category", category.pop())
        loader.add_value("stock", 1)
        loader.add_value("brand", brand)
        if price < 40:
            loader.add_value('shipping_cost', 4.8)
        yield loader.load_item()
