
import re
from decimal import Decimal
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class PerrysCarsSpider(BaseSpider):
    name = 'trustford-perrys.co.uk'
    allowed_domains = ['perrys.co.uk']
    start_urls = ['http://www.perrys.co.uk/cars-offers-lease-nearlynew/page/1']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        cars_urls = hxs.select('//div[@class="resultTiles"]/div[contains(@class, "resRow")]/div/h6/a/@href').extract()
        for url in cars_urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_car)

        if cars_urls:
            current_page = int(response.url.split('/')[-1])
            next = 'http://www.perrys.co.uk/cars-offers-lease-nearlynew/page/' + str(current_page+1)
            yield Request(urljoin_rfc(base_url, next))

    def parse_car(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        brand = hxs.select('//@data-manufacturer').extract()[0]
        status = hxs.select('//div[@id="detMainL"]/h4/text()').extract()[0]

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('identifier', response.url.split('offer-')[-1])
        name = ' '.join(''.join(hxs.select('//h1[@class="detTitle"]//text()').extract()).split())
        loader.add_value('name', name)
        loader.add_value('brand', brand)
        loader.add_value('category', 'New cars')
        loader.add_value('url', response.url)
        price = hxs.select('//p[@class="price"]/text()').extract()
        loader.add_value('price', price)
        image_url = hxs.select('//img[@class="img-responsive"]/@src').extract()
        if image_url:
            loader.add_value('image_url', image_url[0])
        yield loader.load_item()
