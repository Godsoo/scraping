
import re
from decimal import Decimal
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class TrustFordLifeStyleEuropeSpider(BaseSpider):
    name = 'trustford-lifestyleeurope.co.uk'
    allowed_domains = ['lifestyleeurope.co.uk']
    start_urls = ['http://www.lifestyleeurope.co.uk/ford/new-car-offers/']


    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        offers_urls = hxs.select('//div[@data-listing-type="cms_listing"]/div//a[@class="labels"]/@href').extract()
        for url in offers_urls:
            yield Request(urljoin_rfc(base_url, url))

        cars_urls = hxs.select('//div[@id="boxList"]/div[contains(@class, "box")]//div[@class="title"]/a/@href').extract()
        for url in cars_urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

        if not offers_urls and not cars_urls:
            for item in self.parse_product(response):
                yield item

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        product_name = hxs.select('//ul[@class="breadcrumb"]/li/text()').extract()[-1]
        if product_name.lower().endswith(' offer'):
            product_name = product_name[:-6]
        if product_name.lower().startswith('new '):
            product_name = product_name[4:]
        elif product_name.lower().startswith('all-new '):
            product_name = product_name[8:]

        product_price = hxs.select('//td[contains(text(), "he Road\'")]/following-sibling::td/text()').re(r'[\d.,]+')

        if product_name and product_price:
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('identifier', product_name)
            loader.add_value('name', product_name)
            loader.add_value('price', product_price)
            loader.add_value('url', response.url)

            yield loader.load_item()
