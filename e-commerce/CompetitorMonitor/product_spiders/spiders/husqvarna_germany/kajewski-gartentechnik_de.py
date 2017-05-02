# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price_eu as extract_price
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.url import url_query_parameter
import re


class KajewskiGartentechnikDeSpider(BaseSpider):
    name = u'kajewski-gartentechnik.de'
    allowed_domains = ['www.kajewski-gartentechnik.de']
    start_urls = [
        'http://www.kajewski-gartentechnik.de/advanced_search_result.php'
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in hxs.select('//div[@class="containerProdListing1"]//strong/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)
        for url in hxs.select('//*[@id="col3_content"]/table//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        product_loader = ProductLoader(item=Product(), selector=hxs)
        image_url = hxs.select('//div[@class="firstPic"]/a/img/@src').extract()
        product_identifier = hxs.select('//div[@class="desc"]//img[contains(@src,"button_info")]/../@href').extract()[0]
        product_identifier = url_query_parameter(product_identifier, 'pID')
        product_name = hxs.select('//div[@class="productInfo1"]/h1/text()').extract()[0].strip()
        product_loader.add_value('identifier', product_identifier)
        product_loader.add_value('name', product_name)
        if image_url:
            product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        price = hxs.select('//span[@class="productNewPrice"]/text()').extract()
        if not price:
            price = hxs.select('//span[@class="price"]/text()').extract()
        price = extract_price(price[0])
        sku_text = hxs.select('//p[@class="basicData"]//text()').extract()
        sku = ''
        for txt in sku_text:
            if 'Art.Nr.:' in txt:
                sku = txt.replace('Art.Nr.:', '').strip()
                break
        product_loader.add_value('sku', sku)
        product_loader.add_value('price', price)
        product_loader.add_value('url', response.url)
        category = hxs.select('//*[@id="box_categories"]//li[@class="activeCat"]/a/text()').extract()
        product_loader.add_value('category', category)
        search_txt = ''.join(hxs.select('//div[@class="desc"]//text()').extract())
        match = re.search(r"Gewicht.*?(?::|kg)*.*?([\d,]+)", search_txt, re.DOTALL | re.IGNORECASE)
        if match:
            try:
                weight = float(match.group(1).replace(',', '.'))
                if weight <= 3:
                    product_loader.add_value('shipping_cost', 4.90)
                elif weight <= 10:
                    product_loader.add_value('shipping_cost', 8.90)
                elif weight <= 19:
                    product_loader.add_value('shipping_cost', 13.90)
                elif weight <= 60:
                    product_loader.add_value('shipping_cost', 22.90)
                elif weight <= 100:
                    product_loader.add_value('shipping_cost', 29.90)
                elif weight <= 150:
                    product_loader.add_value('shipping_cost', 39.90)
                elif weight <= 220:
                    product_loader.add_value('shipping_cost', 42.90)
                elif weight > 220:
                    product_loader.add_value('shipping_cost', 49)
            except:
                pass
        in_stock = hxs.select('//*[@id="cart_quantity"]//input[@name="products_qty"]')
        if not in_stock:
            product_loader.add_value('stock', 0)
        product = product_loader.load_item()
        yield product