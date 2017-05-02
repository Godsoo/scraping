# -*- coding: utf-8 -*-

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import HtmlResponse, Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin, urlsplit, urlunsplit
from product_spiders.utils import extract_price2uk, fix_spaces
import json
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

STOCK_URL = 'http://api.bestbuy.ca/availability/products?callback=apiAvailability&accept-language=en&postalCode=M5G2C3&skus='


class BestBuyCa(BaseSpider):
    name = "bestbuy.ca"
    allowed_domains = ["bestbuy.ca"]
    start_urls = ["http://www.bestbuy.ca/Search/SearchResults.aspx?filter=%253bbrandName%253aLEGO"]


    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        product_urls = hxs.select('//div[@class="prod-info"]/h4/a/@href').extract()
        for url in product_urls:
            yield Request(urljoin(base_url, url), callback=self.parse_product)

        next_page_url = hxs.select('//li[@class="pagi-next"]/a/@href').extract()
        if next_page_url:
            yield Request(urljoin(base_url, next_page_url[0]), callback=self.parse)

    def parse_product(self, response):
        data = response.xpath('//script/text()').re('var context = ({.+?});')
        data = json.loads(data[0])
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(selector=hxs, item=Product())

        loader.add_xpath('name', '//span[contains(@id, "ProductTitle")]/text()')

        split_url = list(urlsplit(response.url))
        url = urlunsplit(split_url[:3]+['', ''])
        loader.add_value('url', url)

        loader.add_value('brand', 'Lego')
        loader.add_value('category', 'Lego')

        price = hxs.select('//div[contains(@class, "prodprice")]/span/text()').extract()[0]
        price = extract_price2uk(price)
        loader.add_value('price', price)

        image_url = data['pdpProduct']['additionalMedia'][0]['url']
        loader.add_value('image_url', urljoin(base_url, image_url))

        loader.add_xpath('sku', '//span[@itemprop="model"]/text()')

        identifier = hxs.select('//span[@itemprop="productid"]/text()').extract()[0]
        loader.add_value('identifier', identifier)

        stock_url = STOCK_URL + identifier
        request = Request(stock_url, callback=self.parse_availability)
        request.meta['loader'] = loader
        yield request

    def parse_availability(self, response):
        stock = response.body.split('(')[-1]
        stock = stock.split(')')[0]
        stock = json.loads(stock)
        stock = stock['availabilities'][0]['shipping']['status']
        if stock == 'SoldOutOnline':
            stock = 0
        elif stock.title() == 'Unknown':
            self.log('Unknown stock')
            raise ValueError
        else:
            stock = 1

        loader = response.meta['loader']
        loader.add_value('stock', stock)
        yield loader.load_item()
