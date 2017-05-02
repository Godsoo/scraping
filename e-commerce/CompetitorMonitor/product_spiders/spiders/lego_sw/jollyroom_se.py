from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price
import re

from scrapy import log


class JollyroomSeSpider(BaseSpider):
    name = 'jollyroom.se'
    allowed_domains = ['jollyroom.se']
    start_urls = ('http://www.jollyroom.se/sok?text=Lego',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        products = hxs.select('//article[@class="productitem"]//div[@class="bottomwrapper"]/a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)
        # parse pagination
        urls = hxs.select('//div[contains(@class, "paging")]/a[not(@class="active")]/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        product_loader = ProductLoader(item=Product(), selector=hxs)
        name = hxs.select('//*[@itemprop="name"]/text()').extract()
        name = name[0].strip() if name else ''

        product_loader.add_value('name', name)
        sku = ''
        for match in re.finditer(r"([\d,\.]+)", name):
            if len(match.group()) > len(sku):
                sku = match.group()
        product_loader.add_value('sku', sku)
        image_url = hxs.select('//img[contains(@class, "productimage") and contains(@class, "main")]/@src').extract()
        product_loader.add_value('image_url', image_url)
        price = hxs.select('//div[@itemprop="offers"]//*[@itemprop="price"]/text()').re(r'[\d,. ]+')[0]\
            .strip().replace(' ', '').replace(',-', '').replace(u'\xa0', '').replace(',', '.')
        product_loader.add_value('price', extract_price(price))
        if product_loader.get_collected_values('price') and product_loader.get_collected_values('price')[0] < 1000:
            product_loader.add_value('shipping_cost', '49')
        identifier = hxs.select('//div[@id="description-extra"]/text()').re('\d+')
        product_loader.add_value('identifier', identifier)
        product_loader.add_value('url', response.url)
        out_stock = hxs.select('//*[@itemprop="availability" and contains(@href, "OutOfStock")]')
        if out_stock:
            product_loader.add_value('stock', 0)
        product = product_loader.load_item()
        yield product
