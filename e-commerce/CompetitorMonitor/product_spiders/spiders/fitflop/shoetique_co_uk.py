
import json
import re

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.url import urljoin_rfc, url_query_parameter
from product_spiders.items import Product, ProductLoader
from scrapy.utils.response import get_base_url
from scrapy.spider import BaseSpider
from product_spiders.utils import extract_price
import urlparse

class ShoetiqueSpider(BaseSpider):
    name = 'shoetique.co.uk'
    allowed_domains = ['shoetique.co.uk']
    start_urls = ('http://www.shoetique.co.uk/ajax/getProductListings?base_url=search%2Fall-products&page_type=productlistings&page_variant=show&all_upcoming_flag[]=78&page=1&manufacturer_id[]=5&manufacturer_id[]=84',)

    def unparse_qs(self, qs):
        new_qs = []
        for key, value in qs.items():
            for val in value:
                new_qs.append("%s=%s" % (key, val))
        return "&".join(new_qs)

    def parse(self, response):
        base_url = get_base_url(response)
        body = json.loads(response.body)
        hxs = HtmlXPathSelector(text=body)
        qs = urlparse.parse_qs(urlparse.urlparse(response.url).query)
        products = hxs.select('//div[@class="product_title"]/a/@href').extract()
        for item in products:
            url = urljoin_rfc(base_url, item)
            yield Request(url, callback=self.parse_product)
        if products:
            if 'page' in qs and qs['page']:
                qs['page'][0] = int(qs['page'][0]) + 1
                url = urljoin_rfc(base_url, "?" + self.unparse_qs(qs))
                yield Request(url, callback=self.parse)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        price = extract_price(hxs.select('//div[@id="product_price_sale_holder"]//span[@class="price"]/span[@class="inc"]/span[@class="GBP"]').extract().pop())
        stock = hxs.select('//span[@class="product_in_stock" and not(contains(@style, "display")) and contains(text(), "Item in Stock")]').extract()
        name = hxs.select('//span[@itemprop="name"]/text()').extract().pop().strip()
        sku = hxs.select('//span[@id="product_reference"]/text()').extract()
        ppid = hxs.select('//input[@name="parent_product_id"]/@value').extract().pop()
        pid = hxs.select('//input[@name="product_id"]/@value').extract().pop()
        identifier = "%s_%s" % (ppid, pid)
        image_url = hxs.select('//img[@class="cloudzoom"][1]/@src').extract()
        brand = "".join(hxs.select('//div[contains(@class, "product_page_right_brand_image")]/a/@title').extract()).split(u"\u2122")

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_value("name", name)
        loader.add_value("identifier", identifier)
        loader.add_value("price", price)
        loader.add_value("url", response.url)

        if sku and "n/a" not in sku:
            loader.add_value("sku", sku.pop())
        if image_url:
            loader.add_value("image_url", urljoin_rfc(base_url, image_url.pop()))
        if stock:
            loader.add_value("stock", 1)
        else:
            loader.add_value("stock", 0)
        if brand:
            loader.add_value("brand", brand[0])
        yield loader.load_item()
