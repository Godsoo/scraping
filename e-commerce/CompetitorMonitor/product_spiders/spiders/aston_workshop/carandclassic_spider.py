import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class CarAndClassicSpider(BaseSpider):
    name = 'astonworkshop-carandclassic.co.uk'
    allowed_domains = ['carandclassic.co.uk']
    start_urls = ['http://www.carandclassic.co.uk/era/2/7/',
                  'http://www.carandclassic.co.uk/era/3/7/'
                  'http://www.carandclassic.co.uk/era/5/7/',
                  'http://www.carandclassic.co.uk/era/6/7/',
                  'http://www.carandclassic.co.uk/era/7/7/',
                  'http://www.carandclassic.co.uk/era/8/7/',
                  'http://www.carandclassic.co.uk/era/9/7/',
                  'http://www.carandclassic.co.uk/era/10/7/']

    re_year = re.compile('(\d\d\d\d)')


    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = hxs.select('//div[@class="item" or @class="item alt"]')
        for product in products:
            private = 'PRIVATE' in ''.join(product.select('div[@class="itemkeypoints"]/ul/li/text()').extract()).upper()
            if not private:
                continue

            loader = ProductLoader(item=Product(), selector=product)
            name = product.select('div[@class="titleAndText"]/a/text()').extract()[0]
            year_strings = self.re_year.findall(name)
            valid = False
            for year in year_strings:
                if int(year)<=1995 and int(year)>1900:
                    valid = True
                    break

            if valid:            
                loader.add_value('name', name)
                url = product.select('div[@class="titleAndText"]/a/@href').extract()
                url = urljoin_rfc(base_url, url[0])
                loader.add_value('url', url)
                loader.add_value('identifier', url.split('/')[-1])
                price = product.select('div/ul/li[@class="price"]/text()').extract()
                price = price[0] if price else '0'
                loader.add_value('price', price)
                yield loader.load_item()

        next = hxs.select('//a[@class="paging" and text()="Next"]/@href').extract()
        if next:
            yield Request(urljoin_rfc('http://www.carandclassic.co.uk/list/7/', next[0]))

