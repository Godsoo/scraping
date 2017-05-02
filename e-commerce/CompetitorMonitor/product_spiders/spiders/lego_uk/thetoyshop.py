import re

from scrapy import log
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)


class TheToyShopSpider(BaseSpider):
    name = 'legouk-thetoyshop.com'
    allowed_domains = ['thetoyshop.com']
    start_urls = ['http://www.thetoyshop.com/brands/lego?q=',
                  'http://www.thetoyshop.com/Lego/Lego-Legends-of-Chima/c/legoloc?q=%3Aprice-desc%3Asuitability%3ABoys']

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        base_url = get_base_url(response)

        hxs = HtmlXPathSelector(response)
        brands = hxs.select(u'//div[@id="all-lego"]//a/@href').extract()
        for url in brands:
            url = urljoin_rfc(base_url, url)
            yield Request(url)

        next_page = hxs.select(u'//li[@class="page next"]/a/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]))

        products = hxs.select(u'//h3[@class="prod_name"]/a/@href').extract()
        for url in products:
            url = urljoin_rfc(base_url, url)
            yield Request(url, callback=self.parse_product)

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return

        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)

        name = hxs.select(u'//div[@class="prod_title"]/h1/text()').extract()
        if not name:
            self.log('ERROR: no product NAME found! URL:{}'.format(response.url))
            return
        else:
            name = name[0].strip()
            loader.add_value('name', name)

        prod_id = hxs.select('//input[@name="productCode"]/@value').extract()
        loader.add_value('identifier', prod_id[0])

        loader.add_value('url', response.url)

        price = hxs.select(u'//h3[@class="prod_price"]/text()').extract()[0].strip()
        if not price:
            self.log('ERROR: no product PRICE found! URL:{}'.format(response.url))
            return
        if price:
            loader.add_value('price', price)

        product_image = hxs.select(u'//a[@id="imageLink"]/img/@src').extract()
        if not product_image:
            self.log('ERROR: no product Image found!')
        else:
            image = urljoin_rfc(get_base_url(response), product_image[0].strip())
            loader.add_value('image_url', image)

        categories = hxs.select(u'//nav[@id="breadcrumb"]/ol/li/a/text()').extract()
        if not categories:
            self.log('ERROR: category not found! URL:{}'.format(response.url))
        else:
            for category in categories:
                loader.add_value('category', category.strip())

        sku = hxs.select('//dl[dt/text()="Manufacturer Number"]/dd/text()').extract()
        if not sku:
            sku = name.split(' ')[-1]
        if not sku:
            self.log('ERROR: no SKU found! URL:{}'.format(response.url))
        else:
            loader.add_value('sku', sku[0].strip())

        out_of_stock = hxs.select('//div[@class="prod_add_to_cart"]/span[@class="out_of_stock"]')
        if out_of_stock:
            loader.add_value('stock', 0)

        loader.add_value('brand', 'Lego')
        yield loader.load_item()
