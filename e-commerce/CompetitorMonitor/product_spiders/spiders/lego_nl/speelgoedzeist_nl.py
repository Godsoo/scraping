from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price_eu
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class SpeelgoedzeistSpider(BaseSpider):
    name = 'speelgoedzeist.nl'
    allowed_domains = ['speelgoedzeist.nl', 'speelgoednl.nl']
    start_urls = ['http://www.speelgoednl.nl/']

    def start_requests(self):
        yield Request('http://www.speelgoednl.nl/lego-te-koop')
        yield Request('http://www.speelgoednl.nl/catalogsearch/result/?q=lego')
        yield Request('http://www.speelgoednl.nl/lego-thema',
                      callback=self.parse_categories)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for product in hxs.select('//div[@class="product-box"]/span[@class="product-name"]/a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), product), callback=self.parse_product, meta=response.meta)
        for page in hxs.select('//div[@class="pages"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), page), callback=self.parse, meta=response.meta)

    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)

        cats = hxs.select('//ul[contains(@class, "category-grid")]')[:-1]\
            .select('./li[contains(@class, "item")]//span[@class="product-name"]/a/@href').extract()

        for url in cats:
            yield Request(url)

    def parse_product(self, response):
        import re
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)

        loader.add_xpath('identifier', '//input[@name="product"]/@value')
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1/text()')

        if hxs.select('//div[@class="product-view"]//span[@class="regular-price"]//span[@class="price"]//text()'):
            loader.add_value('price', extract_price_eu(''.join(hxs.select('//div[@class="product-view"]//span[@class="regular-price"]//span[@class="price"]//text()').extract())))
        else:
            loader.add_value('price', extract_price_eu(''.join(hxs.select('//div[@class="product-view"]//p[@class="special-price"]//span[@class="price"]//text()').extract())))

        sku = ''.join(hxs.select('//h1/text()').extract())
        try:
            loader.add_value('sku', re.search('(\d{3}\d*)', sku).groups()[0])
        except AttributeError:
            self.log('Not SKU for %s' % (response.url))

        loader.add_xpath('category', '//div[@class="breadcrumbs"]//li[last()-1]/a/text()')

        img = hxs.select('//img[@id="image"]/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        loader.add_value('brand', 'lego')
#        loader.add_value('shipping_cost', '0')
        if hxs.select('//input[@id="qty"]'):
            loader.add_value('stock', '1')
        else:
            loader.add_value('stock', '0')

        loader.add_value('shipping_cost', '6.75')

        yield loader.load_item()
