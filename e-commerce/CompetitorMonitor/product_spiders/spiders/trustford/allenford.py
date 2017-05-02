from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)


class TrustFordAllenfordSpider(BaseSpider):
    name = 'trustford-allenford.com'
    allowed_domains = ['allenford.com']
    start_urls = ['http://www.allenford.com/new-car-offers/']

    handle_httpstatus_list = [404]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        region_urls = response.xpath('//h3/a/@href').extract()

        for url in region_urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_cars)

    def parse_cars(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        cars_urls = hxs.select('//h3/a/@href').extract()
        for url in cars_urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_cars)

        if not cars_urls:
            for car in self.parse_car_details(response):
                yield car



    def parse_car_details(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        product_name = hxs.select('//h1/following-sibling::h2/text()').extract()
        product_price = hxs.select('.//td[contains(text(), "Cash Price")]//text()').re(r'[\d,.]+')
        product_img = hxs.select('//source[@class="responsive-image"]/@data-placeholder').extract()
        if product_img:
            product_img = urljoin_rfc(base_url, product_img[-1])

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('identifier', product_name)
        loader.add_value('name', product_name)
        loader.add_value('price', product_price)
        loader.add_value('url', response.url)
        loader.add_value('image_url', product_img)

        yield loader.load_item()
