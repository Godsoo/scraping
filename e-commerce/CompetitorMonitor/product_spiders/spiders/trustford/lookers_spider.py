import json
import re
from decimal import Decimal
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price

from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class LookersSpider(BaseSpider):
    name = 'trustford-lookers.co.uk'
    allowed_domains = ['lookers.co.uk']
    start_urls = ['http://www.lookers.co.uk/new-cars/']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        yield Request('http://www.lookers.co.uk/ford/new-offers/', callback=self.parse_offers_ford)
        
        brands = hxs.select('//div[@class="container"]//div[contains(@class, "jump")]/div/a/@href').extract()
        for url in brands:
            yield Request(urljoin_rfc(base_url, url))

        models = hxs.select('//div[@class="cycle-inner"]/div/a/@href').extract()
        for url in models:
            yield Request(urljoin_rfc(base_url, url))

        cars_urls = hxs.select('//div[@class="inset"]//a[@class="btn"]/@href').extract()
        for url in cars_urls:
            yield Request(urljoin_rfc(base_url, url))

        name = hxs.select('//div[contains(@class, "title")]/h3/span[@class="variant"]/text()').extract()
        if name:
            model = hxs.select('//div[contains(@class, "title")]/h3/span[@class="model"]/text()').extract()
            if model:
                name = model[0] + ' ' + name[0]
            else:
                name = name[0]

            cap_id = re.findall('CAPID=(\d+)&', response.body)
            if not cap_id:
                log.msg('PRODUCT WITHOUT IDENTIFIER: ' + response.url)
                return

            brand = hxs.select('//div[contains(@class, "title")]/h3/span[@class="make"]/text()').extract()[0]
       
            loader = ProductLoader(item=Product(), response=response)
            cap_id = cap_id[0]
            loader.add_value('identifier', cap_id)
            loader.add_value('name', name)
            loader.add_value('brand', brand)
            loader.add_value('category', 'New cars')
            loader.add_value('url', response.url)
            image_url = hxs.select('//div[@class="span8"]/div[contains(@class, "custom-imag")]/div[@class="inner"]/img/@src').extract()
            if image_url:
                loader.add_value('image_url', image_url[0])
            try:
                price = hxs.select('//div[@class="price-now"]/span[@class="value"]/text()').extract()[0]
            except IndexError:
                price = 0
            loader.add_value('price', price)
            product = loader.load_item()

            yield product

    def parse_offers_ford(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        models = hxs.select('//div[@class="cycle-inner"]/div/a/@href').extract()
        for url in models:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_offers_ford_cars)
        
    def parse_offers_ford_cars(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        models = hxs.select('//section[@class="inner"]/div[@id]')
        if not models:
            models = hxs.select('//section[@class="inner"]/div[.//h1][1]')
        for i, model in enumerate(models):
            loader = ProductLoader(item=Product(), selector=model)
            name = model.select('.//h1[1]/text()').re('(.+?)\s-') or model.select('.//h1[1]/text()').extract()
            if not name:
                continue
            name = name[0]
            loader.add_value('name', name.title())
            loader.add_value('brand', 'Ford')
            loader.add_value('identifier', '-'.join(name.lower().split()))
            loader.add_value('category', 'New cars offers')
            loader.add_value('url', response.url)
            loader.add_xpath('price', './following-sibling::div//tr[normalize-space(./td/text())="Cash Price"]/td[2]/text()')
            yield loader.load_item()
