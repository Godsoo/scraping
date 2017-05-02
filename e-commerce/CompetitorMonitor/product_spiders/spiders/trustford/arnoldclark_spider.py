import re
import json
from scrapy import Spider
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class ArnoldClarkSpider(Spider):
    name = 'trustford-arnoldclark.com'
    allowed_domains = ['arnoldclark.com']
    start_urls = ['https://www.arnoldclark.com/used-cars/search?search_type=New%20Cars&make=&model=&payment_type=monthly'
                  '&min_price=&max_price=&location=&distance=&photos_only=false&unreserved_only=false&keywords='
                  '&body_type[]=&fuel_type=&transmission=&mpg=&colour[]=&roadtax_cost=&mileage=&doors[]=&seats[]=&age=&min_engine_size='
                  '&max_engine_size=&dor=&branch_id=&branch_name=&sort_order=monthly_payment_up&page=1']

    def parse(self, response):
        cars_urls = response.xpath('//h2[contains(@class, "ac-vehicle__title")]/a/@href').extract()
        for url in cars_urls:
            yield Request(response.urljoin(url), callback=self.parse_car)

        next_page = response.xpath('//a[contains(@class, "next")]/@href').extract()
        if next_page:
            yield Request(response.urljoin(next_page[0]))


    def parse_car(self, response):
        data = re.findall('var dataLayer = \[(.*)\];', response.body)[0]
        data = json.loads(data)

        brand = data['vehiclesMake']

        loader = ProductLoader(item=Product(), response=response)
        identifier = data['vehiclesStockRef']
        loader.add_value('identifier', identifier)
        name = ' '.join(''.join(response.xpath('//h1[contains(@class, "ac-vehicle__title")]//text()').extract()).split())
        loader.add_value('name', name)
        loader.add_value('brand', brand)
        loader.add_value('category', 'New cars')
        loader.add_value('url', response.url)
        price = response.xpath('//tr[th[contains(text(), "Cash price")]]//span[@class="ac-money"]/text()').extract()
        loader.add_value('price', price)
        image_url = response.xpath('//div[@class="ac-result__image"]/a/img/@src').extract()
        if image_url:
            loader.add_value('image_url', image_url[0])
        yield loader.load_item()
