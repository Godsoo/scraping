import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, canonicalize_url
from product_spiders.items import (Product,
        ProductLoaderWithNameStrip as ProductLoader)


class ProCameraShopSpider(BaseSpider):
    name = "procamerashop.com"
    allowed_domains = ["procamerashop.co.uk", "www.procamerashop.co.uk"]
    start_urls = ("http://www.procamerashop.co.uk/",)

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        cat_urls = hxs.select("//div[@class='nav-container']/ul/li/a/@href").extract()
        for cat_url in cat_urls[1:]:
            yield Request(
                    url=canonicalize_url(cat_url),
                    callback=self.parse_category)

    def parse_category(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        product_urls = hxs.select("//ul/li[contains(@class,'sec')]/div/div/a/@href").extract()
        for product_url in product_urls:
            yield Request(
                    url=canonicalize_url(product_url),
                    callback=self.parse_product)

        next_page = hxs.select("//div[@class='pages']/ol/li/a[contains(@class,'next')]/@href").extract()
        if next_page:
            yield Request(
                    url=canonicalize_url(next_page[0]),
                    callback=self.parse_category)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(response=response, item=Product())
        loader.add_value('url', response.url)
        loader.add_xpath('name', "//div[@class='product-detail']//div[@class='product-name']/h1/text()")
        loader.add_xpath('price', "//div[@class='product-detail']//span[contains(@class,'price')]/span/text()")
        sku = hxs.select("//div[@class='product-detail']/div[@class='colRight']/p[1]")[0].re('Ref\. Code: (\d+)')
        loader.add_value('sku', sku)
        loader.add_value('identifier', sku)

        yield loader.load_item()
