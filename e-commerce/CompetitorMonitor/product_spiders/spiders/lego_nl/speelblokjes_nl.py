import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price_eu
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class SpeelblokjesSpider(BaseSpider):
    name = 'speelblokjes.nl'
    allowed_domains = ['speelblokjes.nl']
    start_urls = ['http://www.speelblokjes.nl/webshop/']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        for cat in hxs.select('//ul[@class="myshp_menu_side_categories_1"]/li[position()>1]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), cat), callback=self.parse_pages)

        for product in hxs.select('//div[contains(@class, "myshp_list_product_")]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), product), callback=self.parse_product, meta=response.meta)

    def parse_pages(self, response):
        hxs = HtmlXPathSelector(response)

        for product in hxs.select('//div[contains(@class, "myshp_list_product_")]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), product), callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)

        loader.add_xpath('identifier', '//td/span[contains(text(), "Artikelnr")]/../../td[2]/text()')
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1/text()')
        loader.add_value('price', extract_price_eu(''.join(hxs.select('//td[@class="myshp_info_price_value"]//text()').extract())))
        sku = ''.join(hxs.select('//h1/text()').extract())
        try:
            loader.add_value('sku', re.search('(\d{3}\d*)', sku).groups()[0])
        except:
            self.log('No SKU for %s' % (response.url))
        loader.add_xpath('category', '//td/span[contains(text(), "Categorie")]/../../td[2]/text()')

        img = hxs.select('//div[@id="myshp_info_image_large"]//a/@href').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        loader.add_value('brand', 'lego')
        if loader.get_output_value('price') > 75:
            loader.add_value('shipping_cost', '0')
        else:
            loader.add_value('shipping_cost', '4.95')
#        loader.add_xpath('stock', '1')

        yield loader.load_item()
