import os
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class StrawberryNetSpider(BaseSpider):
    name = 'netthandelen-strawberrynet.com'
    allowed_domains = ['strawberrynet.com']
    start_urls = ['http://no.strawberrynet.com/']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        categories = hxs.select('//div[@id="topMenuContainer"]/a/@href').extract()
        for category in categories:
            request = Request(urljoin_rfc(base_url, category), callback=self.parse_category)
            yield request

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        brands = hxs.select('//div[@class="branditems"]/div[@class="brandDiv"]/a/@href').extract()
        for brand in brands:
            request = Request(urljoin_rfc(base_url, brand), callback=self.parse_brand)
            yield request

    def parse_brand(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        brand = ''.join(hxs.select('//div[@class="brandHeader"]/text()').extract())


        # there was exact match to row rowcolor or row2 before
        products = hxs.select('//div[contains(@class,"itemList")]//div[contains(@class,"row2")]')

        for product in products:
            options = ''.join(product.select('div/div/div[@class="col5"]/a[not(@class="tbnaddtocart")]/@href').extract())
            if options:
                yield Request(urljoin_rfc(get_base_url(response), options), callback=self.parse_brand, meta={'brand': brand})
            else:
                loader = ProductLoader(item=Product(), selector=product)
                name = ' '.join(product.select('.//a[@class="whitebglink-prod"]/text()').extract())
                loader.add_value('name', ' '.join((brand, name)))
                price = ''.join(product.select('div/div/div[@class="col4"]/div/span/text()').extract()).replace(',', '.').replace('\r', '').replace(' ', '')
                loader.add_value('price', price)

                product_url = product.select('.//a[@class="whitebglink-prod"]/@href').extract()[0]
                loader.add_value('url', urljoin_rfc(base_url, product_url))
                loader.add_value('identifier', urljoin_rfc(base_url, product_url))
                loader.add_xpath('sku', 'a[@name]/@name')
                yield loader.load_item()
