import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class WehkampSpider(BaseSpider):
    name = 'wehkamp.nl'
    allowed_domains = ['wehkamp.nl']
    start_urls = ['http://www.wehkamp.nl/speelgoed-games/lego/C25_K58/']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for product in hxs.select('//ul[@id="articleList"]/li[@id]/a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), product), callback=self.parse_product)

        for page in hxs.select('//div[contains(@class, "pagination")]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), page))

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)

        price = ''.join(hxs.select('//div[@class="prijs"]//text()').extract())

        if not price:
            price = hxs.select('//div[@class="priceblock"]/span[@class="price"]/text()').extract()

        loader.add_xpath('identifier', '//input[@id="ArtikelNummer"]/@value')
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1//text()')
        loader.add_value('price', price)
        sku = ' '.join(hxs.select('//h1/text()').extract())
        try:
            loader.add_value('sku', re.search('(\d{4}\d*)', sku).groups()[0])
        except:
            self.log('Product without SKU: %s' % (response.url))
        loader.add_xpath('category', '//div[@id="crumbtrail"]/a[last()]/text()')

        img = hxs.select('//div[@id="productVisual"]//img/@src').extract()
        if not img:
            img = hxs.select('//img[@id="mainImage"]/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        loader.add_value('brand', 'lego')
#        loader.add_xpath('stock', '1')

        loader.add_value('shipping_cost', '5.95')

        if loader.get_output_value('identifier'):
            yield loader.load_item()
