# -*- coding: utf-8 -*-

import re
import json
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price_eu as extract_price


class MyTelecomSpider(BaseSpider):
    name = 'eservicesgroup-es-mytelecom.es'
    allowed_domains = ['mytelecom.es']
    start_urls = ['http://www.mytelecom.es/es']

    product_id_regex = re.compile(r'''id_product\s*=\s*\'(\d*)\';''')

    def __init__(self, *args, **kwargs):
        super(MyTelecomSpider, self).__init__(*args, **kwargs)

        self.current_cookie = 0

    def start_requests(self):
        yield Request('http://www.mytelecom.es/es')
        yield Request('http://www.mytelecom.es/sitemap.xml', callback=self.parse_sitemap)

    def parse_sitemap(self, response):
        categories = re.findall('<loc>(.*?/c/.*/\d+)</loc>', response.body)
        for url in categories:
            if not 'data:' in url:
                yield Request(url)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        # we extract the categories urls
        categories = hxs.select('//nav[@id="mainNavInner"]//a[not(contains(@href, "producto")) and not(@href="#")]/@href').extract()
        for category in categories:
            yield Request(urljoin_rfc(base_url, category))

        categories = hxs.select('//nav[@id="mainNav"]/ul/li')
        for category in categories:
            menu_products = category.select('.//div[@class="product"]/a/@href').extract()
            categories = category.select('a/text()').extract()
            for menu_product in menu_products:
                self.current_cookie += 1
                yield Request(urljoin_rfc(base_url, menu_product),
                              callback=self.parse_product,
                              meta={'categories': categories,
                                    'cookiejar': self.current_cookie})

        products = hxs.select('//a[@class="prod_name"]/@href').extract()
        for product in products:
            categories = hxs.select('//ul[@class="breadcrumbs"]//text()').extract()[2:]
            categories = [category for category in categories if '>' not in category]
            self.current_cookie += 1
            yield Request(urljoin_rfc(base_url, product),
                          callback=self.parse_product,
                          meta={'categories': categories,
                                'cookiejar': self.current_cookie})

        next_page = hxs.select('//li[@class="next"]/a/@href').extract()
        if next_page:
           yield Request(urljoin_rfc(base_url, next_page[0]))

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), response=response)

        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1[@class="prod_name"]/text()')
        in_stock = 'EN STOCK' in ''.join(hxs.select('//span[contains(@class, "prod_stock_text")]/text()').extract()).upper()
        if not in_stock:
            loader.add_value('stock', 0)

        for category in response.meta['categories']:
            loader.add_value('category', category)

        loader.add_xpath('brand', '//li[span[contains(text(), "Fabricante")]]/text()')
        loader.add_value('shipping_cost', 6.99)
        loader.add_xpath('sku', u'//li[span[contains(text(), "Cod. Artículo")]]/text()')

        identifier = hxs.select('//input[@id="JS_google_remarketing__prodid"]/@value').extract()

        loader.add_value('identifier', identifier)
        image_url = hxs.select('//ul[@class="etalage"]//img/@src').extract()
        if image_url:
            loader.add_value('image_url', image_url[0])
        product = loader.load_item()

        meta = response.meta.copy()
        meta['product'] = product

        cart_url = 'http://www.mytelecom.es/es/ajax_cart_update/only_minicart:true'
        data = {'product_id': product['identifier'], 'quantity': '1', 'view_minicart': 'front_cart/v_modal_add_cart'}
        yield FormRequest(cart_url, formdata=data,
                          headers={'Accept': 'application/json, text/javascript, */*; q=0.01',
                                   'X-Requested-With': 'XMLHttpRequest'}, dont_filter=True,
                          meta=meta,
                          callback=self.parse_price)


    def parse_price(self, response):
        data = json.loads(response.body)
        hxs = HtmlXPathSelector(text=data['htmlMiniCart'])

        price = ''.join(hxs.select('//div[@class="prod_price_cnta"]/div[@class="prod_price"]//text()[not (contains(../@class, "text-muted"))]').extract())
        price = ''.join(re.findall('([\d\.,]+)', price))
        price = extract_price(price)

        product = Product(response.meta['product'])
        product['price'] = price

        yield product
