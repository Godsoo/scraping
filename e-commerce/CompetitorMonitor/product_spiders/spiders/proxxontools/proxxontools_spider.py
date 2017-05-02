import os
import logging

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class ProxxonToolsSpider(BaseSpider):
    name = 'proxxon-tools.com'
    allowed_domains = ['proxxon-tools.com']
    start_urls = ['http://www.proxxon-tools.com']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//small/a[@class="product_section"]/@href').extract()
        for category in categories:
            url = urljoin_rfc(get_base_url(response), category)
            yield Request(url, callback=self.parse_products)

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select("//div[@class='rightbox']//div[@id='ContentPage']/table[last()]/tr/td")
        products_found = False
        if products:
            for product in products:
                name = product.select(".//h2//text()").extract()
                if not name:
                    name = product.select(".//h3//text()").extract()
                identifier = product.select(".//prices/@prod_ref").extract()
                if not identifier:
                    identifier = product.select('.//input[@type="image"]/@name').extract()
                url = urljoin_rfc(get_base_url(response), ''.join(product.select('div/h2[@class="product"]/a/@href').extract()))
                price = product.select('.//td[1]/span[@class="actlarge"]/text()').extract()

                if not identifier and not price:
                    url = urljoin_rfc(get_base_url(response), ''.join(product.select('.//h4/a/@href').extract()))
                    yield Request(url, callback=self.parse_products)

                if not name:
                    logging.error("NO NAME!!! %s" % response.url)
                    continue
                name = " ".join(name[0].split())  # fix whitespaces

                if not identifier:
                    logging.error("NO IDENTIFIER!!! %s - %s" % (name, response.url))
                    continue
                identifier = identifier[0]
                if "!" in identifier:
                    identifier = identifier.split('!')[-1]
                if "_" in identifier:
                    identifier = identifier.split('_')[-1]

                if not price:
                    logging.error("NO PRICE!!! %s - %s" % (name, response.url))
                    continue
                price = price[0]

                loader = ProductLoader(item=Product(), selector=product)
                loader.add_value('name', name)
                loader.add_value('sku', identifier)
                loader.add_value('identifier', identifier)
                loader.add_value('url', url)
                loader.add_value('price', price)
                yield loader.load_item()
                products_found = True
        if not products_found:
            categories = hxs.select('//span/table/tr//td/a/@href').extract()
            for category in categories:
                url = urljoin_rfc(get_base_url(response), category)
                yield Request(url, callback=self.parse_products)

            for product_link in hxs.select('//div[@class="product_list"]/div/h2/a/@href').extract():
                url = urljoin_rfc(get_base_url(response), product_link)
                yield Request(url, callback=self.parse_products)

