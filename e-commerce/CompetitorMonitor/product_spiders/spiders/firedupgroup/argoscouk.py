import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoader

import logging


class FireplaceworldCoUkSpider(BaseSpider):
    name = 'argos.co.uk'
    allowed_domains = ['argos.co.uk']
    start_urls = (
        'http://www.argos.co.uk/static/Search/searchTerms/FIREPLACE.htm',
        'http://www.argos.co.uk/webapp/wcs/stores/servlet/Search?storeId=10001&catalogId=1500002951&langId=-1&searchTerms=WINDSOR+OAK+AND+BLACK',
        'http://www.argos.co.uk/webapp/wcs/stores/servlet/Search?storeId=10001&catalogId=1500002951&langId=-1&searchTerms=IRAD',
        )

    def parse(self, response):
        URL_BASE = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        # check if individual product page or products list
        name = hxs.select("//div[@id='pdpProduct']/h1/text()").extract()
        if name:
            name = name[0].strip()
            url = response.url
            price = hxs.select("//div[@id='pdpPricing']/span[@class='actualprice']/span/text()").extract()
            if not price:
                logging.error("ERROR!! NO PRICE!! %s " % url)
                return
            product = Product()
            loader = ProductLoader(item=product, response=response)
            loader.add_value('url', url)
            loader.add_value('name', name)
            loader.add_value('price', price)
            loader.add_value('sku', '')
            yield loader.load_item()
            return
            #continue if not

        # pages
        page_urls = hxs.select("//div[contains(@class, 'pagination')]//a[@class='button']/@href").extract()
        for url in page_urls:
            url = urljoin_rfc(URL_BASE, url)
            yield Request(url)

        # products list
        products = hxs.select("//div[@id='products']/ul/li[contains(@class, 'item')]/dl")
        if not products:
            logging.error("ERROR!! NO PRODUCTS!! %s " % response.url)
        for product_el in products:
            name = product_el.select('dt[@class="title"]/a/text()').extract()
            if not name:
                logging.error("ERROR!! NO NAME!! %s" % response.url)
                continue
            name = name[0].strip()

            url = product_el.select('dt[@class="title"]/a/@href').extract()
            if not url:
                logging.error("ERROR!! NO URL!! %s %s" % (response.url, name))
                continue
            url = url[0]

            price = product_el.select('dd[@class="price"]/span[@class="main"]/text()').extract()
            if not price:
                logging.error("ERROR!! NO PRICE!! %s %s" % (response.url, name))
                continue
            price = price[0]

            product = Product()
            loader = ProductLoader(item=product, response=response)
            loader.add_value('url', url)
            loader.add_value('name', name)
            loader.add_value('price', price)
            loader.add_value('sku', '')
            yield loader.load_item()
