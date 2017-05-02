

from scrapy.selector import HtmlXPathSelector
from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price2uk

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
import re
import string

class GunsAndPowderSpider(BaseSpider):
    name = 'gunsandpowder.dk'
    allowed_domains = ['www.gunsandpowder.dk']
    start_urls = ['http://www.gunsandpowder.dk']

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        productCategories = hxs.select('//div[@class="navigation_content"]//a/@href').extract()
        for url in productCategories:
            yield Request(urljoin_rfc(base_url, url), meta=response.meta, callback=self.parseProductPage)


    def parseProductPage(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//div[@class="productlist section"]//div[@class="product"]').extract()
        for product in products:
            hxs2 = HtmlXPathSelector(text=product)
            loader = ProductLoader(item=Product(), selector=hxs2)
            loader.add_xpath('name', '//div[@class="name"]/a/text()')
            priceText = hxs2.select('//span[@class="price"]/text()').extract()
            loader.add_value('price', self.decodeDanishPriceString(priceText[0]))
            url = urljoin_rfc(get_base_url(response),  hxs2.select('//td[@class="readmore"]/a/@href').extract()[0])
            loader.add_value('url', url)
            yield loader.load_item()

    def decodeDanishPriceString(self, pString):
        priceRe = re.compile("([0-9.]*),([0-9]*) DKK")
        priceMatch = priceRe.match(pString)
        price = float(string.replace(priceMatch.group(1), '.', ''))
        price += float(priceMatch.group(2))/100
        return price
            



        

        
