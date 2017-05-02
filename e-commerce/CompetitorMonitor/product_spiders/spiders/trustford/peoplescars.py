
import re
from decimal import Decimal
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader


class TrustFordPeoplesCarsSpider(BaseSpider):
    name = 'trustford-peoplescars.co.uk'
    allowed_domains = ['peoplescars.co.uk']
    start_urls = ['http://www.peoplescars.co.uk/new-car-offers/']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        cars_urls = hxs.select('//div[@class="button module"]/a[@title="View Offer"]/@href').extract()
        for url in cars_urls:
            if "managers-specials/" in url:
                yield Request(urljoin_rfc(base_url, url), callback=self.special_offers)
            else:
                yield Request(urljoin_rfc(base_url, url), callback=self.parse_car)

    def special_offers(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        cars_urls = hxs.select('//div[@class="cycle off"]/a/@href').extract()
        for url in cars_urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_car)


    def parse_car(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        identifier = response.url.split('/')[-2]

        price = hxs.select('//td[contains(text(), "Cash Price")]/following-sibling::td/text()').extract()
        if not price:
            price = hxs.select('//h2/text()').re('Manager\'s Special Price (.*)')
        if not price:
            return

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('identifier', identifier)

        name = hxs.select('//div[@class="textInner"][./h2]/*//strong/text()').extract()
        if name:
            name = name[0]
        loader.add_value('name', name)
        loader.add_value('url', response.url)
        loader.add_value('price', price)

        yield loader.load_item()
