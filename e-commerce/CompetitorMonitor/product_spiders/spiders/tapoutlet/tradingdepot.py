import re
import json

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class TradingDepotSpider(BaseSpider):
    name = 'tradingdepot.co.uk'
    allowed_domains = ['tradingdepot.co.uk']
    start_urls = ['http://www.tradingdepot.co.uk/DEF/home']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for category in hxs.select(u'//div[@id="lh_nav"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), category))

        for product in hxs.select(u'//div[contains(@class,"productlist")]/table//tr/td[@class="descr"]/a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), product), callback=self.parse_product)

        for page in hxs.select(u'//div[@class="pagenav"]/a[@class="next"]/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), page))

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        category = hxs.select(u'//div[@class="breadcrumb"]/a/text()').extract()
        if category:
            category = category[-1]

        loader = ProductLoader(item=Product(), selector=hxs)

        identifier = re.search(u'!!(.*)!!', response.url).group(1)
        loader.add_value('identifier', identifier)
        sku = hxs.select(u'//p[contains(text(),"MPN")]/em/text()').extract()
        if sku:
            loader.add_value('sku', sku[0].replace(' ', ''))
        loader.add_value('url', response.url)
        name = hxs.select(u'//form/h1/text()').extract()
        loader.add_value('name', name[0].strip())
        price = hxs.select(u'//div[@class="productdetail"]/h1/span[@id="pricespan"]/text()').extract()
        price = price[0].strip()
        loader.add_value('price', price)
        loader.add_value('category', category)

        img = hxs.select(u'//div[@class="productimage"]/a/img/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        loader.add_xpath('brand', u'//p[contains(text(),"Brand")]/em/text()')
        yield loader.load_item()
