import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class BrickfeverSpider(BaseSpider):
    name = 'brickfever.nl'
    allowed_domains = ['brickfever.nl']
    start_urls = ['http://www.brickfever.nl/?pagina=webshop&artikelgroep=1']
    ids = {}

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for category in hxs.select(u'//div[@id="menu"]//a[@id="catblok"]'):
            yield Request(urljoin_rfc(get_base_url(response), category.select(u'./@href')[0].extract()),
                          meta={'category': category.select(u'./div[@id="cattitel"]/text()')[0].extract()})

        for product_group in hxs.select(u'//div[@id="productgroepen"]/a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), product_group), meta=response.meta)

        for product in hxs.select(u'//div[@id="artikel"]//a[@id="titel"]/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), product), callback=self.parse_product, meta=response.meta)

        for page in hxs.select(u'//td[@id="rechts"]/a[@id="arrow"][1]/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), page))

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        identifier = re.search('artikel=(.*)&?', response.url).group(1)
        try:
            price = extract_price(hxs.select('//div[@id="details"]//td[@class="extra"][2]/text()').extract().pop())
        except:
            return

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//div[@id="content"]/div/h1/text()')
        loader.add_value('price', price)
        loader.add_value('category', response.meta.get('category') or u'')

        img = hxs.select(u'//a[@id="hoofdfoto"]/@style').re('background-image:url\((.*)\)')
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        loader.add_value('brand', 'lego')
        out_of_stock = u'NIET OP VOORRAAD' in ''.join(hxs.select('//td[@class="voorraad"]/text()').extract()).strip().upper()
        if out_of_stock:
             loader.add_value('stock', 0)
        if identifier not in self.ids or price != self.ids[identifier]:
            self.ids[identifier] = price
            yield loader.load_item()
