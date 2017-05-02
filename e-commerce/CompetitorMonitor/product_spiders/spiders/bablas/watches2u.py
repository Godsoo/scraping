import re
import os
import csv
from decimal import Decimal, ROUND_DOWN
from w3lib.url import add_or_replace_parameter

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.item import Item, Field
from urlparse import urljoin as urljoin_rfc

from product_spiders.items import Product
from bablas_item import ProductLoader

def format_price(price):
    if price is None:
        return ''
    # try to convert to Decimal
    if not isinstance(price, Decimal):
        # convert integer
        if isinstance(price, int):
            price = Decimal(price)
        # convert float
        elif isinstance(price, float):
            price = Decimal(price)
        # convert string
        elif isinstance(price, basestring):
            # check if it's a number
            try:
                float(price)
                price = Decimal(price)
            except ValueError:
                pass

    return str(price.quantize(Decimal('0.01'), rounding=ROUND_DOWN))

class WatchesMeta(Item):
    discount_price = Field()
    discount_percentage = Field()


class Watches2USpider(BaseSpider):
    name = 'watches2u.com'
    allowed_domains = ['watches2u.com']
    start_urls = ('http://www.watches2u.com/find.do?sorting=price-ASC',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        category_urls = []  # hxs.select(u'').extract()
        for url in category_urls:
            url = urljoin_rfc(base_url, url)
            yield Request(url)

        product_urls = hxs.select('//div[@id="xcomponent_searchres_products"]//a/@href').extract()
        for url in product_urls:
            url = urljoin_rfc(base_url, url)
            yield Request(url, callback=self.parse_product)

        next_page = response.xpath(u'//a[@class="next"]/@onclick').extract()
        if next_page:
            page_num = re.search('page_num=([\d]+)', next_page[0]).group(1)
            url = add_or_replace_parameter(response.url, 'page_num', page_num)
            yield Request(url)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = hxs.select('//div[@class="xcomponent_products_container"]//a[@class="xcomponent_products_medium_link"]/@href').extract()
        if products:
            for product in products:
                yield Request(urljoin_rfc(base_url, product), callback=self.parse_product)


        loader = ProductLoader(item=Product(), response=response)

        sku = hxs.select(u'//span[@itemprop="sku"]/text()').extract()
        if not sku:
            hxs.select(u'//span[@class="siblings_title"]/span/text()').re('\((.*)\)')
        if not sku:
            return
        sku = sku[0].strip() if sku else ''

        category = hxs.select(u'//div[@itemprop="breadcrumb"]/a/text()').extract()
        category = category[-2].strip() if category else ''
        brand = hxs.select(u'//span[@itemprop="brand"]/text()').extract()
        brand = brand[0].strip() if brand else ''

        name = hxs.select(u'//span[@itemprop="name"]/text()').extract()
        if not name:
            return
        name = name.pop().strip()

        loader.add_value('name', u'%s %s %s' % (brand, name, sku))
        loader.add_value('brand', brand)
        loader.add_value('category', category)
        loader.add_value('sku', sku)
        loader.add_value('identifier', sku)
        loader.add_value('url', response.url)
        price = hxs.select(u'//meta[@itemprop="price"]/@content').extract()
        price = price[0].replace(',', '') if price else ''
        loader.add_value('price', price)
        image = hxs.select(u'//img[@itemprop="image"]/@src').extract()
        image = image[0] if image else ''
        loader.add_value('image_url', urljoin_rfc(get_base_url(response), image))
        stock = hxs.select(u'//div[@class="stockdetail"]/text()').re('Only (One) Left.')
        if stock:
            stock = 1
        else:
            stock = hxs.select(u'//div[@class="stockdetail"]/text()').re('Last (One) Ever In Stock ')
            if stock:
                stock = 1
            else:
                stock = hxs.select(u'//div[@class="stockdetail"]/text()').re('In Stock, ([\d]+)')
                if stock:
                    stock = int(stock[0])
                else:
                    out_of_stock = hxs.select(u'//div[@class="stockout"]/text()').re('Out Of Stock')
                    if out_of_stock:
                        stock = 0
        if stock or stock == 0:
            loader.add_value('stock', stock)

        product = loader.load_item()

        product['metadata'] = WatchesMeta()

        promo = hxs.select('//a[@class="page_products_details4_aimage"][1]/@onclick').re(r'(\d+)%')
        if not promo:
            promo = hxs.select('//div[contains(@class, "page_products_details5_top_aimages")]/a/@onclick').re(r'(\d+)%')
        if promo:
            promo = Decimal(promo[0])
            product['metadata']['discount_price'] = format_price(loader.get_output_value('price') - \
                                                                 (loader.get_output_value('price') * (promo / 100)))
            product['metadata']['discount_percentage'] = str(promo) + '%'
        else:
            product['metadata']['discount_price'] = ''
            product['metadata']['discount_percentage'] = ''

        yield product
