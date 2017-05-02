from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from product_spiders.items import Product, ProductLoader
from scrapy.utils.response import get_base_url
from scrapy.spider import BaseSpider
from product_spiders.utils import extract_price
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
import re


class MaxikovyhrackyCzSpider(BaseSpider):
    name = 'maxikovy-hracky.cz'
    allowed_domains = ['maxikovy-hracky.cz']
    start_urls = ('http://www.maxikovy-hracky.cz/katalog/stavebnice/stavebnice-lego',)
    ids = []

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        for url in hxs.select('//div[contains(@class, "subcats")]/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_category)

    def parse_category(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//table[@id="catalogue_prods"]/tr/td/h3/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

        for url in hxs.select('//div[contains(@class, "paging")]/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse)

    def parse_product(self, response):
        def get_sku(name):
            res = re.findall("([0-9]{3,5}).*", name)
            if res:
                return res.pop()
            else:
                return ""

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        name = hxs.select('//h2/text()').extract().pop().strip()
        price = extract_price(hxs.select(u'//td[contains(text(), "Va\u0161e cena")]/following-sibling::td/text()').extract().pop().replace(" ", ""))
        sku = get_sku(hxs.select(u'//td[contains(text(), "K\xf3d zbo\u017e\xed")]/following-sibling::td/text()').extract().pop())

        identifier = hxs.select(u'//td[contains(text(), "K\xf3d zbo\u017e\xed")]/following-sibling::td/text()').extract().pop()

        category = hxs.select('//div[contains(@class, "path")]/a/text()').extract()
        brand = "Lego"

        image_url = hxs.select('//div[@class="prod-image"]/a/img/@src').extract()

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
        if identifier not in self.ids:
            self.ids.append(identifier)
            yield loader.load_item()
