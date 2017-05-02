import os

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class ArcEuroTradeSpider(BaseSpider):
    name = 'arceurotrade.co.uk_arceurotrade'
    allowed_domains = ['arceurotrade.co.uk', 'www.arceurotrade.co.uk']
    start_urls = (u'http://www.arceurotrade.co.uk/quick-index.aspx', )

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        categories = hxs.select(u'//li[@class="QuickIndexLink"]/a/@href').extract()
        categories += hxs.select(u'//div[@class="DepartmentName"]/a/@href').extract()
        categories += hxs.select(u'//dl[@id="Navigation"]//a/@href').extract()
        for url in categories:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url)

        for product in self.parse_product(response):
            yield product

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        products = hxs.select(u'//table[@id="ProdTable"]//tr')
        for product in products:
            name = product.select(u'./td[2]/text()')[0].extract().split()
            price = product.select(u'./td[3]/text()')[0].extract().strip()
            price = price[1:] if price[0] == u'\xa3' else price
            sku = product.select(u'./td[1]/text()')[0].extract()
            image_url = product.select("./../../div[@class='TextDescription']/img/@src").extract()
            if not image_url:
                image_url = product.select("./../../div[@class='DiscriptionText']/div[@class='Image']/img/@src").extract()

            loader = ProductLoader(item=Product(), selector=product)
            loader.add_value('url', response.url)
            loader.add_value('name', sku)
            loader.add_value('name', name)
            loader.add_value('price', price)
            loader.add_value('sku', sku)
            loader.add_value('identifier', sku)
            if image_url:
                image_url = urljoin_rfc(get_base_url(response), image_url[0])
                loader.add_value('image_url', image_url)

            # if loader.get_output_value('price'):
            yield loader.load_item()
