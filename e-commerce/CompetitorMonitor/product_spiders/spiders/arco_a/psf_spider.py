# -*- coding: utf-8 -*-
import re
from urlparse import urljoin as urljoin_rfc

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price


class PsfSpider(BaseSpider):
    name = 'arco-a-psf.co.uk'
    allowed_domains = ['psf.co.uk']
    start_urls = ('http://www.psf.co.uk',)

    def _start_requests(self):
        yield Request('http://www.psf.co.uk/styles/17838-westminster-trouser-navy-37-unfinished', callback=self.parse_product)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories_urls = hxs.select('//ul[contains(@class, "nav")]/li/a/@href').extract()
        for url in categories_urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product_list)

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories_urls = hxs.select('//ul[contains(@class, "nav")]/li//a[not(contains(@href, "brand"))]/@href').extract()
        categories_urls += hxs.select('//ul[contains(@class, "brand-sub-nav")]/li//a/@href').extract()
        for url in categories_urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product_list)

        products_urls = response.css('div.prod_inner a::attr(href)').extract()
        for url in products_urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

        for nextp in hxs.select('//ul[@class="pagination"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, nextp.replace('%5B', '[').replace('%5D', ']')), callback=self.parse_product_list)
        

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        try:
            product_id = re.findall('\/(\d+)-', response.url)[-1]
        except IndexError:
            product_id = re.findall('\/(\d+)$', response.url)[-1]
            
        name = hxs.select('//div[@class="pm_inner"]/h1/text()').extract_first()
        sku = hxs.select('//span[contains(@class, "product_code")]/text()').extract()
        sku = sku[0] if sku else ''
        if not name:
            name = sku        
        if not name:
            for request in self.parse_product_list(response):
                yield request
            return
        category = hxs.select('//ul[contains(@class, "ancestors")]/li/a/text()').extract()
        if category:
            category = category[-1]
        image_url = hxs.select('//div[@class="mlens-image"]//img/@src').extract()
        if image_url:
            image_url = urljoin_rfc(base_url, image_url[0])
        brand = hxs.select('//a[@class="more" and contains(@href, "brands")]/h2/text()').re('More (.*)')
        brand = brand[0].strip() if brand else ''


        price = ''.join(hxs.select('//span[@class="pm_price"]//text()').extract())
        price = extract_price(price)
        
        options = hxs.select('//select[@id="basket_line_product_id"]/option[@value!=""]')
        row_options = hxs.select('//tr[@class="no_stock" or @class="has_stock"]')
        if options:
            for option in options:
                size = option.select('text()').extract()[0]
                product_loader = ProductLoader(item=Product(), selector=option)
                product_loader.add_value('category', category)

                product_name = name+' - '+size

                brand_in_name = False
                for w in re.findall('([a-zA-Z]+)', product_name):
                    if w.upper() in brand.upper():
                        brand_in_name = True

                if brand.upper() not in product_name.upper() and brand.upper() not in ('OTHER', 'UNASSIGNED') and not brand_in_name:
                    product_name = brand + ' ' + product_name

                product_loader.add_value('name', product_name)
                product_loader.add_value('url', response.url)
                option_id = option.select('@value').extract()[0]
                product_loader.add_value('identifier', product_id+'-'+option_id)
                product_loader.add_value('brand', brand)
                product_loader.add_value('sku', sku)
                #stock = option.select('div[@class="pr_stock"]/text()').extract()[0]
                #add_button = option.select('.//input[contains(@class, "addbasket")]')
                #if add_button:
                #    product_loader.add_value('stock', 1)
                #else:
                #    product_loader.add_value('stock', extract_price(stock))
                if price < 150:
                    product_loader.add_value('shipping_cost', 6)
            
                product_loader.add_value('price', price)
                product_loader.add_value('image_url', image_url)
                yield product_loader.load_item()
        elif row_options:
            for option in row_options:
                size = option.select('./td[1]/text()').extract()[0]
                product_loader = ProductLoader(item=Product(), selector=option)
                product_loader.add_value('category', category)

                product_name = name+' - '+size

                brand_in_name = False
                for w in re.findall('([a-zA-Z]+)', product_name):
                    if w.upper() in brand.upper():
                        brand_in_name = True

                if brand.upper() not in product_name.upper() and brand.upper() not in ('OTHER', 'UNASSIGNED') and not brand_in_name:
                    product_name = brand + ' ' + product_name

                product_loader.add_value('name', product_name)
                product_loader.add_value('url', response.url)
                option_id = option.select('./td[3]/input[1]/@value').extract()[0]
                product_loader.add_value('identifier', product_id+'-'+option_id)
                product_loader.add_value('brand', brand)
                product_loader.add_value('sku', sku)
                #stock = option.select('div[@class="pr_stock"]/text()').extract()[0]
                #add_button = option.select('.//input[contains(@class, "addbasket")]')
                #if add_button:
                #    product_loader.add_value('stock', 1)
                #else:
                #    product_loader.add_value('stock', extract_price(stock))

                price = ''.join(option.select('./td[2]/div[not(@class="oldprice")]/div[@class="nowprice"]/text()').extract())
                if not price:
                    price = ''.join(option.select('./td[2]//text()').extract())

                price = extract_price(price)
                if price < 150:
                    product_loader.add_value('shipping_cost', 6)
            
                product_loader.add_value('price', price)
                product_loader.add_value('image_url', image_url)
                yield product_loader.load_item()
        else:
            product_loader = ProductLoader(item=Product(), response=response)
            product_loader.add_value('category', category)
            
            product_name = name

            brand_in_name = False
            for w in re.findall('([a-zA-Z]+)', product_name):
                if w.upper() in brand.upper():
                    brand_in_name = True

            if brand.upper() not in product_name.upper() and brand.upper() not in ('OTHER', 'UNASSIGNED') and not brand_in_name:
                product_name = brand + ' ' + product_name

            product_loader.add_value('name', product_name)
            product_loader.add_value('url', response.url)

            product_loader.add_value('identifier', product_id)
            product_loader.add_value('brand', brand)
            product_loader.add_value('sku', sku)
            if price < 150:
                product_loader.add_value('shipping_cost', 6)
            
            product_loader.add_value('price', price)
            product_loader.add_value('image_url', image_url)
            yield product_loader.load_item()
