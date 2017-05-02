from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from product_spiders.items import Product, ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price_eu
from scrapy.http import Request

from heimkaupitems import HeimkaupProduct as Product


class TolvutekIsSpider(BaseSpider):
    name = 'tolvutek.is'
    allowed_domains = ['tolvutek.is']
    start_urls = ('http://tolvutek.is',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//div[@id="leftbar"]/div/ul/li/a/@href').extract()
        for url in categories:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = hxs.select('//div[contains(@class, "productItem")]/a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

        pages = hxs.select('//div[@class="paginator"]/div/a/@href').extract()
        for url in pages:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_category)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        name = hxs.select('//div[@id="mainbigbar"]/h2/text()').extract()
        if not name:
            return

        price = extract_price_eu(hxs.select('//div[contains(@class, "displayPrice")]/text()').extract().pop())

        identifier = hxs.select('//input[@name="productId"]/@value').extract().pop()

        category = hxs.select('//div[@id="breadcrumb"]/span/a/text()').extract()
        if len(category) > 1:
            category = " > ".join(category[1:])
        else:
            category = ""

        image_url = hxs.select('//a[contains(@class, "mainimage")]/@href').extract()

        sku = hxs.select(u'//span[@class="modelnr"][contains(text(), "V\xf6run\xfamer:")]/text()').re(".*: (.*)")

        stock = hxs.select('//div[@class="status"]/span/text()').extract()

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_value('name', name.pop())
        loader.add_value('price', price)
        loader.add_value('identifier', identifier)
        loader.add_value('sku', sku)
        loader.add_value('category', category)
        loader.add_value('url', response.url)
        if u'S\xe9rp\xf6ntun' in stock:
            loader.add_value('stock', 1)
        elif u'V\xe6ntanlegt' in stock:
            loader.add_value('stock', 0)
        if sku:
            loader.add_value('sku', sku.pop())
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        yield loader.load_item()
