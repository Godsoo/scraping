import re
import json

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy.http.cookies import CookieJar
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from itertools import product
from collections import defaultdict

from utils import extract_price


class TotalFishingTackleSpider(BaseSpider):
    name = 'angling_direct-total_fishing_tackle.com'
    allowed_domains = ['total-fishing-tackle.com']
    start_urls = ('http://www.total-fishing-tackle.com/', 'http://www.total-fishing-tackle.com/fishing-clothing-footwear-sale', 'http://www.total-fishing-tackle.com/fishing-rod-sale')

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        cats = hxs.select('//ol[@class="nav-primary"]//li/a/@href').extract()
        for url in cats:
            yield Request(urljoin_rfc(base_url, url))

        subcats = hxs.select('//dl[@id="narrow-by-list"]/dd/ol/li/a[contains(@href, "cat")]/@href').extract()
        for url in subcats:
            yield Request(urljoin_rfc(base_url, url.split('?')[0]))

        next_page = hxs.select('//a[@class="next i-next"]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]))

        products = hxs.select('//h2[@class="product-name"]/a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

        #if hxs.select('//div[@id="productReviewLink"]') and hxs.select('//h1/*[@class="productGeneral"]/text()'):
        #    yield Request(response.url, callback=self.parse_product, meta={'dont_merge_cookies': True})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        product_identifier = hxs.select('//input[@name="product"]/@value')[0].extract()
        sku = ''
        product_name = hxs.select('//div[@class="product-name"]/span/text()')[0].extract().strip()
        base_price = response.xpath('//p[@class="special-price"]/span[@class="price"]/text()').extract()
        if not base_price:
            base_price = response.xpath('//span[@class="regular-price"]/span[@class="price"]/text()').extract()
        base_price = extract_price(base_price[0]) if base_price else 0
        #cart_price = hxs.select('//div[@class="cartBoxTotal"]/text()').extract()
        image_url = hxs.select('//img[@id="image-main"]/@src').extract()
        image_url = urljoin_rfc(base_url, image_url[0]) if image_url else ''
        category = hxs.select('//span[@typeof="v:Breadcrumb"]/a/text()').extract()
        category = category[-1] if category else ''
        brand = hxs.select('//ul[@id="productDetailsList"]/li[contains(text(),"Manufactured")]/text()').re('Manufactured by: (.*)')

        options = hxs.select('//select[@class=" required-entry product-custom-option"]/option')
        data_config = response.xpath('//script/text()').re('new Product.Config\((.+)\);')
        if options:
            for option in options:
                identifier = option.select('./@value').extract()
                if not identifier or identifier[0] == '':
                    continue
                else:
                    identifier = identifier[0]
                option_name = option.select('./text()').extract()[0]
                option_name = option_name.split(u'+\xa3')[0].strip()
                name = product_name + " " + option_name
                price = extract_price(option.select('@price').extract()[0])

                identifier = product_identifier + "-" + identifier
                loader = ProductLoader(response=response, item=Product())
                loader.add_value('identifier', identifier)
                loader.add_value('sku', product_identifier)
                loader.add_value('price', base_price + price)
                loader.add_value('brand', '')
                loader.add_value('url', response.url)
                loader.add_value('name', name)
                loader.add_value('image_url', image_url)
                loader.add_value('category', category)
                if not loader.get_output_value('price'):
                    loader.add_value('stock', 0)
                yield loader.load_item()
            return

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_value('identifier', product_identifier)
        loader.add_value('sku', product_identifier)
        loader.add_value('url', response.url)
        loader.add_value('name', product_name)
        loader.add_value('image_url', image_url)
        loader.add_value('brand', brand)
        loader.add_value('category', category)
        loader.add_value('price', base_price)
        if not loader.get_output_value('price'):
            loader.add_value('stock', 0)
        item = loader.load_item()
        
        if data_config:
            data = json.loads(data_config[0])['attributes']
            products = dict()
            for attribute in sorted(data):
                for option in data[attribute]['options']:
                    for product in option['products']:
                        if not products.get(product):
                            products[product] = dict()
                            products[product]['label'] = option['label']
                            products[product]['price'] = extract_price(option['price'])
                        else:
                            products[product]['label'] += ' ' + option['label']
                            products[product]['price'] += extract_price(option['price'])
            for product in products:
                loader = ProductLoader(item=Product(), response=response)
                loader.add_value(None, item)
                loader.add_value('name', products[product]['label'])
                loader.replace_value('identifier', product_identifier + '-' + product)
                loader.replace_value('sku', product)
                loader.replace_value('price', base_price + products[product]['price'])
                yield loader.load_item()
            return

        yield item
