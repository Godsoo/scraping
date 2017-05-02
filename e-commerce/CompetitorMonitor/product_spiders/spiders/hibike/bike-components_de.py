import re
import urllib

from decimal import Decimal
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy import log

from product_spiders.utils import extract_price

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class BikeComponentsDeSpider(BaseSpider):
    name = 'bike-components.de'
    allowed_domains = ['bike-components.de']
    start_urls = ('http://www.bike-components.de',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select(u'//div[@class="module-nav-categories"]/ul/li/a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product_list)

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select(u'//a[@class="categoryButton"]/@href').extract():
            url = urljoin_rfc(get_base_url(response), url.strip())
            yield Request(url, callback=self.parse_product_list)

        for url in hxs.select(u'//ul[@class="products clearfix"]/li/a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url.strip())
            yield Request(url, callback=self.parse_product)

        next_page = hxs.select(u'//a[contains(@title,"next page")]/@href').extract()
        if next_page:
            url = urljoin_rfc(get_base_url(response), next_page[0])
            yield Request(url, callback=self.parse_product_list)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('url', response.url)
        product_loader.add_xpath('name', u'normalize-space(//h1/text())')

        product_loader.add_xpath('sku', u'//input[@name="products_id"]/@value');
        product_loader.add_xpath('category', u'//div[@class="module-subcategories"]/ul/li/a[@class="selected"]/text()')

        img = hxs.select('//ul[@class="site-product-images"]/li/a/img/@src').extract()
        if img:
            product_loader.add_value('image_url', img[0])
        product_loader.add_xpath('brand', u'normalize-space(//span[@class="manufacturer"]/a/text())')
#            product_loader.add_xpath('shipping_cost', '')
        product = product_loader.load_item()

        options = [(op, desc, price) for (op, desc, price) in \
                    zip(hxs.select('//div[@id="module-product-item-cart-options"]/select/option[not(@value="")]/@value').extract(),
                        hxs.select('//div[@id="module-product-item-cart-options"]/select/option/@data-selectedtext').extract(),
                        hxs.select('//div[@id="module-product-item-cart-options"]/select/option/@data-price').extract()) if op]

        for id, option, price in options:
            # model || unit price || delivery status
            if 'EUR' not in price:
                continue
            prod = Product(product)
            info = option
            prod['identifier'] = prod['sku'] + ':' + id
            prod['name'] = prod['brand'] + ' ' + prod['name'] + ' ' + info
            prod['price'] = Decimal(re.search('([\d\.,]+)', price).groups()[0].replace('.', '').replace(',', '.'))
            yield prod
