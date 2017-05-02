# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc
import urlparse
import urllib


class JonesandtomlinCoUkSpider(BaseSpider):
    name = u'jonesandtomlin.co.uk'
    allowed_domains = ['www.jonesandtomlin.co.uk']
    start_urls = [
        'http://www.jonesandtomlin.co.uk/'
    ]

    def _start_requests(self):
        yield Request('http://www.jonesandtomlin.co.uk/p-2269-tom-schneider-serpent-shelves.html', callback=self.parse_product)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        #menu
        for url in hxs.select('//ul[@id="mainmenu"]/li/a/@href').extract():
            params = {'rpp': '9999'}
            url_parts = list(urlparse.urlparse(url))
            query = dict(urlparse.parse_qsl(url_parts[4]))
            query.update(params)
            url_parts[4] = urllib.urlencode(query)
            url = urlparse.urlunparse(url_parts)
            yield Request(urljoin_rfc(base_url, url), self.parse_products)

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        #categories
        for url in hxs.select('//ul[@class="filterlist"]/li//a/@href').extract():
            params = {'rpp': '9999'}
            url_parts = list(urlparse.urlparse(url))
            query = dict(urlparse.parse_qsl(url_parts[4]))
            query.update(params)
            url_parts[4] = urllib.urlencode(query)
            url = urlparse.urlunparse(url_parts)
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products)
        #products
        for url in hxs.select('//div[@class="iconlistlarge"]//li/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        image_url = hxs.select('//span[@class="productimage main"]//img/@src').extract()
        #product_identifier = hxs.select('//input[@name="product"]/@value').extract()[0].strip()
        product_name = ' '.join(hxs.select('//div[@class="producttitle"]/h1/text()').extract())
        category = hxs.select('//p[@id="crumbs"]/a/text()').extract()
        category = category[-1].strip() if category else ''
        brand = hxs.select('//div[@class="producttitle"]/div/a/img/@alt').extract()
        brand = brand[0].strip() if brand else ''

        options = hxs.select('//div[contains(@class, "optionblock")]')
        if options:
            for option in options:
                product_loader = ProductLoader(item=Product(), selector=hxs)
                option_name = ' '.join(option.select('.//div[@class="optiondetails"]/h3/text()').extract())
                option_name = option_name.replace(u'\xa0', '')
                product_loader.add_value('name', product_name + option_name)
                identifier = option.select('.//div[@class="stocklevelblock"]/@id').extract()[0]
                identifier = identifier.split('_')[0]
                product_loader.add_value('identifier', identifier)
                sku = option.select('.//div[@class="optiondetails"]/p[@class="footnote"]/text()').extract()[0]
                sku = sku.replace('Code: ', '')
                product_loader.add_value('sku', sku)
                if image_url:
                    product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
                price = option.select('.//div[@class="optionprices"]/p[@class="productyoupay"]/text()').extract()
                if price:
                    price = extract_price(price[0].strip().replace(u'\xa3', ''))
                    product_loader.add_value('price', price)
                else:
                    product_loader.add_value('price', 0)
                product_loader.add_value('url', response.url)
                if brand:
                    product_loader.add_value('brand', brand)
                if category:
                    product_loader.add_value('category', category)
                product = product_loader.load_item()
                yield product
        else:
            product_loader = ProductLoader(item=Product(), selector=hxs)
            product_loader.add_value('name', product_name)
            identifier = hxs.select('//input[@name="bprod"]/@value').extract()[0]
            product_loader.add_value('identifier', identifier)
            sku = hxs.select('.//div[@class="productcolumn2"]/p[@class="footnote"]/text()').extract()[0]
            sku = sku.replace('Code: ', '')
            product_loader.add_value('sku', sku)
            if image_url:
                product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            price = hxs.select('//p[@class="productblock productyoupay"]/text()').extract()
            if price:
                price = extract_price(price[0].strip().replace(u'\xa3', ''))
                product_loader.add_value('price', price)
            else:
                product_loader.add_value('price', 0)
            product_loader.add_value('url', response.url)
            if brand:
                product_loader.add_value('brand', brand)
            if category:
                product_loader.add_value('category', category)
            product = product_loader.load_item()
            yield product
