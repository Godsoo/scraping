from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.contrib.loader.processor import TakeFirst, Join, Compose
from urlparse import urljoin
from product_spiders.items import Product, ProductLoader

from scrapy import log


class hamleysSpider(BaseSpider):
    name = u'legouk-hamleys.com'
    allowed_domains = [u'www.hamleys.com', u'hamleys.com']
    start_urls = [u'http://www.hamleys.com/build-it-lego.irc']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        links = hxs.select('//li[@class="productThumbName"]/a/@href').extract()
        for link in links:
            yield Request(urljoin(get_base_url(response), link), callback=self.parse_product)

        next = hxs.select('//a[@id="nextpagebutton"]/@href').extract()
        if next:
            yield Request(urljoin(get_base_url(response), next[0]))

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        
        try:
            name = hxs.select('//*[@itemprop="name"]/text()').extract().pop().strip()
        except IndexError:
            yield Request(response.url.replace('hamleys.com/', 'hamleys.com/detail.jsp?pName=').replace('.ir', ''), callback=self.parse_product)
            return

        out_of_stock = 'OUT OF STOCK' in ''.join(hxs.select('//li[@class="stockStatus"]/span/text()').extract()).upper()


        # cat_regex = 'LEGO Duplo|LEGO Bricks and More|LEGO Bricks|LEGO Creator|LEGO City|LEGO Ninjago|LEGO Monster Fighters|LEGO Super Heros|LEGO Lord Of The Rings|LEGO Star Wars|LEGO Games'

        loader = ProductLoader(response=response, item=Product())
        loader.add_value('url', urljoin(base_url, response.url))
        loader.add_value('name', name)
        loader.add_xpath('image_url', '//img[@class="productMain"]/@src', TakeFirst())
        loader.add_xpath('price', '//div[@class="productprice "]/text()', Join(''), re="([.0-9]+)")
        category = hxs.select('//div[@class="pagetopnav"]/ul[contains(@class, "crumb")]/li/a/text()').extract()[-2]
        loader.add_value('category', category)
        loader.add_value('sku', name, re=' (\d\d\d+)\s*$')
        loader.add_value('brand', 'LEGO')
        identifier = hxs.select('//*[@itemprop="productID"]/text()').extract()[0].replace('Code: ', '')
        loader.add_value('identifier', identifier)

        if out_of_stock:
            loader.add_value('stock', 0)

        yield loader.load_item()
