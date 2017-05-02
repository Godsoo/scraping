from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class PistonHeadsSpider(BaseSpider):
    name = 'astonworkshop-pistonheads.com'
    allowed_domains = ['pistonheads.com']
    start_urls = ['http://www.pistonheads.com/classifieds?Category=used-cars&M=220&M=1322&M=2266&M=2265&M=1667&M=2150&M=219&M=218&M=1162&M=915&M=2506&M=2484&M=1224&M=2354&M=1175&M=2151&M=222&M=1161&M=1311&M=221&M=1546&M=2270&M=223&Page=1&TradePrivateFilter=Private&YearFrom=0&YearTo=1995']


    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = hxs.select('//div[@class="result-contain"]')
        for product in products:
            loader = ProductLoader(item=Product(), selector=product)
            loader.add_xpath('name', './/div[@class="listing-headline"]/a/h3/text()')
            url = product.select('.//div[@class="listing-headline"]/a/@href').extract()
            url = urljoin_rfc(base_url, url[0])
            loader.add_value('url', url)
            loader.add_xpath('identifier', './/div[@class="listing-utils"]/a/i/@id')
            price = product.select('.//span[@class="price"]/text()').extract()
            price = price[0].replace(',', '') if price else '0'
            loader.add_value('price', price)
            yield loader.load_item()

        next = hxs.select('//li[not(contains(@class, "disabled"))]/a[@id="next"]/@href').extract()
        if next:
            yield Request(urljoin_rfc(base_url, next[0]))

