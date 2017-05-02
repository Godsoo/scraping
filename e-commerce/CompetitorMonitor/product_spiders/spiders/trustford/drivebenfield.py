
import re
from decimal import Decimal
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
import os
import csv

HERE = os.path.abspath(os.path.dirname(__file__))


class TrustFordDriveBenfieldSpider(BaseSpider):
    name = 'trustford-drivebenfield.co.uk'
    allowed_domains = ['drivebenfield.com']
    start_urls = ['https://www.drivebenfield.com/new/cars/ford/deals']

    def __init__(self, *argv, **kwargs):
        super(TrustFordDriveBenfieldSpider, self).__init__(*argv, **kwargs)

        self.models = []

        with open(os.path.join(HERE, 'trustford_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.models.append(row['model'])

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        cars_urls = response.xpath('//h2[@class="vehicle-card__heading"]/a/@href').extract()
        for url in cars_urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_car)

    def parse_car(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        car_variant = hxs.select('//h1[@class="local-header__heading"]/text()').extract()[0].strip()

        car = hxs.select('//dt[contains(text(), "Model")]/following-sibling::dd/text()').extract()[0].strip()
        model = ''
        for client_model in self.models:
            if client_model in car_variant:
                model = client_model
                break
        engine = hxs.select('//dt[contains(text(), "Engine Size")]/following-sibling::dd/text()').extract()[0].strip()
        power = hxs.select('//dt[contains(text(), "Engine Power")]/following-sibling::dd/text()').extract()[0].strip()
        year = hxs.select('//dt[contains(text(), "Year")]/following-sibling::dd/text()').extract()
        year = year[0].strip() if year else ''
        doors = hxs.select('//dt[contains(text(), "Doors")]/following-sibling::dd/text()').extract()[0].strip()

        product_name = ' '.join([car, model, engine, power, year, doors])
        product_price = hxs.select('//dl[dt/text()="Cash price"]/dd/text()').re(r'[\d.,]+')

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('identifier', re.search(r'/(\d+)', response.url).group(1))
        loader.add_value('name', product_name)
        loader.add_value('price', product_price)
        loader.add_value('url', response.url)

        yield loader.load_item()
