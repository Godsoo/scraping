from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from utils import extract_price_eu
from product_spiders.items import (
    Product,
    ProductLoaderEU as ProductLoader
)


class MediamarktSpider(BaseSpider):
    name = 'electronicarts-saturn.de'
    allowed_domains = ['saturn.de']

    start_urls = ['http://www.saturn.de']

    def start_requests(self):
        product_urls = [
            'http://www.saturn.de/mcs/product/Battlefield-4-Action-PC,48352,419161,1061604.html?langId=-3',
            'http://www.saturn.de/mcs/product/Battlefield-Hardline-Action-PC,48352,521570,1335378.html?langId=-3#technische-daten',
            'http://www.saturn.de/mcs/product/Dragon-Age%3A-Inquisition-Rollenspiel-PC,48352,521570,1258312.html?langId=-3',
            'http://www.saturn.de/mcs/product/FIFA-15-Sport-PC,48352,521570,1335438.html?langId=-3',
            'http://www.saturn.de/mcs/product/Plants-vs.-Zombies%3A-Garden-Warfare-%28Code-In-A-Box%29-Action-PC,48352,419161,1321424.html?langId=-3',
            'http://www.saturn.de/mcs/product/SimCity-Simulation-PC,48352,419161,522686.html?langId=-3',
            'http://www.saturn.de/mcs/product/Die-Sims-3-Simulation-PC,48352,419161,519805.html?langId=-3',
            'http://www.saturn.de/mcs/product/Die-Sims-3---Starter-Set-Simulation-PC,48352,419161,711593.html?langId=-3',
            'http://www.saturn.de/mcs/product/Die-Sims-4-%28Limited-Edition%29-Simulation-PC,48352,521570,945283.html?langId=-3',
            'http://www.saturn.de/mcs/product/Titanfall-Action-PC,48352,419161,883726.html?langId=-3',
        ]

        for url in product_urls:
            yield Request(url)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('identifier', '//*[@itemprop="sku"]/text()')
        loader.add_xpath('name', '//*[@itemprop="name"]/text()')
        loader.add_value('url', response.url)
        loader.add_xpath('price', '//*[@itemprop="price"]/text()')
        loader.add_xpath('image_url', '//*[@itemprop="image"]/@src', lambda imgs: map(lambda img: urljoin_rfc(base_url, img), imgs))

        yield loader.load_item()
