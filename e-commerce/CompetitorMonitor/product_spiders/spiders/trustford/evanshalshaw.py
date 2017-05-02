
import re
import json
from decimal import Decimal
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url


from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class TrustFordEvansHalshawSpider(BaseSpider):
    name = 'trustford-evanshalshaw.com'
    allowed_domains = ['evanshalshaw.com']
    start_urls = ['http://www.evanshalshaw.com/brands/ford/ford-new-car-offers/']

    collected_product_names = {}


    def parse(self, response):
        url = 'http://www.evanshalshaw.com/Services/UnifiedSpecialOffer.asmx/GetSpecialOffers'
        formdata = {"Make": "Ford",
                    "TargetedAt": "Private",
                    "VehicleType": "Car",
                    "Range": None,
                    "FinanceType": None,
                    "OfferType": "New",
                    "WebsiteID": "1"}
        req = Request(url, method='POST', body=json.dumps(formdata), headers={'Content-Type':'application/json'}, callback=self.parse_products)
        yield req

    def parse_products(self, response):
        base_url = get_base_url(response)

        data = json.loads(response.body)
        products = data['d']['Data']
        for product in products:
            yield Request(urljoin_rfc(base_url, product['Data']['WebsiteURL']), 
                          callback=self.parse_product, meta={'identifier': product['Data']['ID']})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        product_name = ' '.join(hxs.select('//h1/text()').extract()[-1].split())
        product_price = hxs.select('//li[contains(text(), "On The Road Cash Price")]/span[@class="detail"]/text()').re(r'[\d,.]+')
        product_price = product_price[-1] if product_price else '0'
        product_image = hxs.select('//img[contains(@id, "Image_MainPhoto")]/@src').extract()

        product_identifier = response.meta['identifier']

        if product_identifier in self.collected_product_names:
            product_name = self.collected_product_names[product_identifier]
        else:
            self.collected_product_names[product_identifier] = product_name

        if product_price:
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('identifier', product_identifier)
            loader.add_value('name', product_name)
            loader.add_value('price', product_price)
            loader.add_value('url', response.url)
            loader.add_value('image_url', product_image)

            yield loader.load_item()
