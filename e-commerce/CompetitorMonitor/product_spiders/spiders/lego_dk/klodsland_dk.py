from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price
from scrapy.http import Request
import re


class KlodslandDkSpider(BaseSpider):
    name = 'klodsland.dk'
    allowed_domains = ['klodsland.dk']
    start_urls = ('http://www.klodsland.dk/',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        #parse categories
        urls = hxs.select('//*[@id="shopmenu"]//a[contains(@href,"group.asp")]/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product_list)

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        #pagination
        urls = hxs.select('//table[@class="group-buttons buttons"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product_list)

        products = hxs.select('//table[@class="group-list"]//tr')
        for product in products:
            product_loader = ProductLoader(item=Product(), selector=product)
            name = product.select('./td[2]//a[1]/b/text()').extract()
            if not name:
                continue
            else:
                name = name[0]
            product_loader.add_value('name', name)
            sku = ''
            for match in re.finditer(r"([\d,\.]+)", name):
                if len(match.group()) > len(sku):
                    sku = match.group()
            product_loader.add_value('sku', sku)
            image_url = product.select('./td[4]//img/@src').extract()[0]
            product_loader.add_value('image_url', urljoin_rfc(base_url, image_url))
            price = product.select('.//font[@id="offer"]/text()').extract()
            if price:
                price = extract_price(price[0].strip().partition('DKK ')[2].replace('.', '').replace(',', '.'))
            else:
                price = product.select('.//span[@class="price"]/text()').extract()[0]
                price = extract_price(price.strip().strip('DKK ').replace('.', '').replace(',', '.'))
            product_loader.add_value('price', price)
            if price < 1000:
                product_loader.add_value('shipping_cost', 49)
            else:
                product_loader.add_value('shipping_cost', 0)
            identifier = product.select('./td[2]/font/a/@href').extract()[0].partition('product=')[2]
            product_loader.add_value('identifier', identifier)
            url = product.select('./td[2]/font/a/@href').extract()[0]
            product_loader.add_value('url', urljoin_rfc(base_url, url))
            product = product_loader.load_item()
            yield product