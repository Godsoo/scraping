import re
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin as urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class WexJessopsSpider(BaseSpider):
    name = 'wexphotographic_new-jessops.com'
    allowed_domains = ['jessops.com']

    start_urls = ['http://www.jessops.com/search?fh_view_size=100']

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//a[@class="productDataUrl"]/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

        for url in hxs.select('//div[@class="pagenumbersboxes"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        loader = ProductLoader(response=response, item=Product())
        loader.add_xpath('identifier', '//input[@name="skuOfferingId1"]/@value')
        sku = hxs.select('//span[@id="mainprodsku"]/text()').re('Product code: (.*)')
        loader.add_value('sku', sku)
        categories = hxs.select('//div[@id="breadcrumbtrail"]/a/text()').extract()[1:]
        brand = re.findall("manufacturerName: '(.*)'", response.body)
        brand = brand[0] if brand else ''
        loader.add_value('brand', brand)
        loader.add_value('category', categories)
        loader.add_xpath('name', '//h1[@itemprop="name"]/text()')
        price = hxs.select('//span[@itemprop="price"]/text()').extract()[0]
        loader.add_value('price', price)
        loader.add_value('url', response.url)
        image_url = hxs.select('//img[@id="imgRegular"]/@src').extract()
        image_url = urljoin_rfc(base_url, image_url[0].strip()) if image_url else ''
        loader.add_value('image_url', image_url)
        stock = hxs.select('//*[@id="homeprodaddto"]//a/text()').extract()
        if stock and 'Out of Stock' in stock[0] or 'Pre-Order' in stock[0]:
            loader.add_value('stock', 0)
        product = loader.load_item()
        yield product
