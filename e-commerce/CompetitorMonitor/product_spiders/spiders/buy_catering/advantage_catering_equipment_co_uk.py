import re
import json
import urlparse
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.base_spiders.prodcache import ProductCacheSpider

class AdvantageCateringEquipmentSpider(ProductCacheSpider):
    name = 'buycatering-advantage-catering-equipment.co.uk'
    allowed_domains = ['advantage-catering-equipment.co.uk']
    start_urls = ('http://advantage-catering-equipment.co.uk',)

    def _start_requests(self):
        yield Request('http://www.advantage-catering-equipment.co.uk/tefcold-blc3-blast-chiller-shock-freezer.html', callback=self.parse_product, meta={'product': Product()})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for cat in hxs.select('//ul[@id="nav"]/li[position()<6]'):
            for url in cat.select('.//a/@href').extract():
                try:
                    yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_cat, meta={'category':cat.select('./a/span/text()').extract()[0]})
                except:
                    pass

    def parse_cat(self, response):
        hxs = HtmlXPathSelector(response)
        for productxs in hxs.select('//li[contains(@class,"item")]'):
            product = Product()
            product['price'] = extract_price(''.join(productxs.select('.//span[starts-with(@id,"price-excluding-tax-")]/text()').extract()))
            if product['price']:
                product['stock'] = 1
            else:
                product['stock'] = 0

            request = Request(urljoin_rfc(get_base_url(response), productxs.select('.//h2/a/@href').extract()[0]), callback=self.parse_product, meta=response.meta)
            yield self.fetch_product(request, self.add_shipping_cost(product))

        for url in hxs.select('//div[@class="pages"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_cat, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=response.meta['product'], selector=hxs)
        loader.add_xpath('identifier', '//input[@name="product"]/@value')
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//*[@itemprop="name"]//text()')
        loader.add_xpath('sku', '//tr/th[contains(text(), "Model Number")]/../td/text()')

        loader.add_value('category', response.meta.get('category'))

        img = hxs.select('//img[@id="product-image-zoom-img"]/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        loader.add_xpath('brand', '//tr/th[contains(text(), "Brand Name")]/../td/text()')
        yield self.add_shipping_cost(loader.load_item())

    def add_shipping_cost(self, item):
        if item.get('price', 0) < 100:
            item['shipping_cost'] = 6.95
        else:
            item['shipping_cost'] = 0
        return item
