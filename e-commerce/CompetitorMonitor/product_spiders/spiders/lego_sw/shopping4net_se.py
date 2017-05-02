from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price
import re


class Shopping4netSeSpider(BaseSpider):
    name = 'shopping4net.se'
    allowed_domains = ['shopping4net.se']
    start_urls = ('http://www.shopping4net.se/Leksaker/Tillverkare/Lego.htm',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        urls = hxs.select('//div[@id="main-content"]//div[@class="row-fluid"]//li/a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)
        # parse pagination
        urls = hxs.select('//div[contains(@class, "pagination")]//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        not_in_stock = hxs.select('//div[@id="ctl00_cphMain_pnlWatchProduct"]').extract()
        if not not_in_stock:
            product_loader = ProductLoader(item=Product(), selector=hxs)
            name = hxs.select('//header[@id="product-header"]//h1/text()').extract()[0]
            product_loader.add_value('name', name)
            sku = ''
            for match in re.finditer(r"([\d,\.]+)", name):
                if len(match.group()) > len(sku):
                    sku = match.group()
            product_loader.add_value('sku', sku)
            image_url = hxs.select('//div[@class="product-image"]//img/@src').extract()[0]
            product_loader.add_value('image_url', urljoin_rfc(base_url, image_url))
            price = hxs.select('//div[@id="proddata"]//span[@class="prices"]//span[@class="amount"]/text()').extract()[0].strip()\
                .replace(' kr', '').replace(' SEK', '').replace(u'\xa0', '').replace(',', '.')
            product_loader.add_value('price', extract_price(price))
            identifier = hxs.select('//div[@id="proddata"]//div[@class="info"]//dd[1]/text()').extract()[0]
            product_loader.add_value('identifier', identifier)
            product_loader.add_value('url', response.url)
            product = product_loader.load_item()
            yield product
