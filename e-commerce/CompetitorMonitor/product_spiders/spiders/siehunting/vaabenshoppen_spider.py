import os
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.fuzzywuzzy import process
from product_spiders.fuzzywuzzy import fuzz

HERE = os.path.abspath(os.path.dirname(__file__))

class VaabenShoppenSpider(BaseSpider):
    name = 'vaabenshoppen.dk'
    allowed_domains = ['vaabenshoppen.dk']
    start_urls = ['http://www.vaabenshoppen.dk']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        categories =  hxs.select('//*[@id="pMenuToplevell0"]/li/a/@href').extract()
        for category in categories:
            url =  urljoin_rfc(get_base_url(response), category)
            yield Request(url, callback=self.parse_categories)

    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//table[@class="Tabular"]/tbody/tr[@class="plistRowOdd" or @class="plistRowEven"]')
        if products:
            for product in products:
                loader = ProductLoader(item=Product(), selector=product)
                loader.add_xpath('name', 'td[2]/a/text()')
                url =  urljoin_rfc(get_base_url(response), product.select('td[2]/a/@href').extract()[0])
                loader.add_value('url', url)
                price = ''.join(product.select('td[4]/a/text()').extract()).replace('.','').replace(',','.')
                loader.add_value('price', price)
                yield loader.load_item()
        else:
            products = hxs.select('//div[@class="prelement"]')
            if products:
                for product in products:
                    loader = ProductLoader(item=Product(), selector=product)
                    loader.add_xpath('name', 'div[@class="prmain"]/a/text()')
                    url =  urljoin_rfc(get_base_url(response), product.select('div[@class="prmain"]/a/@href').extract()[0])
                    loader.add_value('url', url)
                    price = ''.join(product.select('div[@class="prbasket"]/p[@class="prpri"]/text()').extract()).replace('.','').replace(',','.')
                    loader.add_value('price', price)
                    yield loader.load_item()
            else:
                products = products = hxs.select('//div[@class="plistAreaHeader"]/div')  
                for product in products:
                    loader = ProductLoader(item=Product(), selector=product)
                    loader.add_xpath('name', 'a/text()')
                    url =  urljoin_rfc(get_base_url(response), product.select('a/@href').extract()[0])
                    loader.add_value('url', url)
                    price = ''.join(product.select('div/div[@class="prbasket"]/p[@class="prpri"]/text()').extract()).replace('.','').replace(',','.')
                    loader.add_value('price', price)
                    yield loader.load_item()
        
        next = hxs.select('//a[@class="plistpagnext"]/@href').extract()
        if next:
            url =  urljoin_rfc(get_base_url(response), next[-1])
            yield Request(url, callback=self.parse_categories)

        sub_cats = hxs.select('//li[a[@class="active"]]/ul/li/a/@href').extract()
        if sub_cats:
            for sub_cat in sub_cats:
                url =  urljoin_rfc(get_base_url(response), sub_cat)
                yield Request(url, callback=self.parse_categories)
        else:
            sub_cats = hxs.select('//*[@id="pMenuSublevelsl1"]/li/a/@href').extract()
            for sub_cat in sub_cats:
                url =  urljoin_rfc(get_base_url(response), sub_cat)
                yield Request(url, callback=self.parse_categories)
