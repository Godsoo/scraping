# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc
import re
import json

from bikenationmeta import BikeNationMeta

from scrapy import log


class SportsbikeshopSpider(BaseSpider):
    name = u'sportsbikeshop.co.uk'
    allowed_domains = ['www.sportsbikeshop.co.uk']
    start_urls = [
        'http://www.sportsbikeshop.co.uk/motorcycle_parts/change_currency/GBP'
    ]
    jar_counter = 0

    def parse(self, response):
        base_url = get_base_url(response)
        url = 'http://www.sportsbikeshop.co.uk/motorcycle_parts/content_group/_/(all;product_rating;DESC;0-0;all)/page_0/max_1000'
        yield Request(urljoin_rfc(base_url, url), callback=self.parse_start)

    def parse_start(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in hxs.select('//div[@class="pagination"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_start)
        for url in hxs.select('//*[@id="prod_list"]//span[@class="info"]/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        image_url = hxs.select('//img[@itemprop="image"]/@src').extract()
        product_name = hxs.select('//h1[@itemprop="name"]/text()').extract()[0].strip()
        category = hxs.select('//*[@id="breadcrumb"]/ul/li[2]/a/text()').extract()
        category = category[0].strip() if category else ''
        brand = hxs.select('//img[@class="prod_man"]/@alt').extract()
        brand = brand[0].strip() if brand else ''

        options = hxs.select('//select[@id="option"]//option')
        if options:
            option = options[0].select('string(.)').extract()[0]
            if option == "See 'Product Options' table below":
                options = options[2:]
                table = True
            else:
                options = options[1:]
                table = False
            stock_info = {}
            for match in re.finditer(r"var option_(\d+) = new Array\(('.*?')\);", response.body):
                stock_info[match.groups()[0]] = json.loads('[{}]'.format(match.groups()[1].replace("'", '"')))
            for option in options:
                option_id = option.select('./@value').extract()[0]
                if not table:
                    option_name = option.select('./text()').extract()
                    if option_name:
                        option_name = option_name[0]
                    else:
                        log.msg('Skip option without name, url:' + response.url)
                        continue
                else:
                    option_name = hxs.select('//tr[@id="option_{}"]/td[@class="description"]/text()'.format(option_id)).extract()[0]
                price = extract_price(stock_info[option_id][0])

                name = product_name + ', ' + option_name
                product_loader = ProductLoader(item=Product(), selector=hxs)
                product_loader.add_value('identifier', option_id)
                product_loader.add_value('name', name)
                if image_url:
                    product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
                product_loader.add_value('price', price)
                product_loader.add_value('url', response.url)
                product_loader.add_value('brand', brand)
                product_loader.add_value('category', category)

                stock_status = ''
                if stock_info[option_id][2] == 'Y':
                    stock_status = 'In stock'
                else:
                    if stock_info[option_id][3] != '0':
                        if stock_info[option_id][3] == 'X':
                            stock_status = 'Awaiting stock'
                        else:
                            if stock_info[option_id][5] == 'P':
                                stock_status = 'Pre-orders being taken'
                            else:
                                stock_status = stock_info[option_id][4]
                    else:
                        possible_status = re.findall("prod_status = '(.*)';", response.body)
                        if possible_status:
                            stock_status = possible_status[-1]

                in_stock = True if price>0 else False
                if not in_stock or stock_status.upper() == 'OUT OF STOCK':
                    product_loader.add_value('stock', 0)

                metadata = BikeNationMeta()
                metadata['stock_status'] = stock_status

                product = product_loader.load_item()

                product['metadata'] = metadata
                self.jar_counter += 1
                yield Request('http://www.sportsbikeshop.co.uk/motorcycle_parts/basket/' + option_id,
                              callback=self.parse_shipping_price1,
                              cookies={},
                              meta={'product': product,
                                    'cookiejar': self.jar_counter})
        else:
            product_loader = ProductLoader(item=Product(), selector=hxs)
            identifier = response.url.rpartition('/')[2]
            product_loader.add_value('identifier', identifier)
            product_loader.add_value('name', product_name)
            if image_url:
                product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            price = hxs.select('//span[@itemprop="price"]/text()').extract()
            price = extract_price(price[0].strip())
            product_loader.add_value('price', price)
            product_loader.add_value('url', response.url)
            product_loader.add_value('brand', brand)
            product_loader.add_value('category', category)

            metadata = BikeNationMeta()
            stock_status = hxs.select('//span[@id="status"]/a/text()').extract()
            metadata['stock_status'] = stock_status[0] if stock_status else ''

            in_stock = True if price>0 else False
            if not in_stock or metadata['stock_status'].upper() == 'OUT OF STOCK':
                product_loader.add_value('stock', 0)

            product = product_loader.load_item()

            product['metadata'] = metadata

            self.jar_counter += 1
            yield Request('http://www.sportsbikeshop.co.uk/motorcycle_parts/basket/' + identifier,
                          callback=self.parse_shipping_price1,
                          cookies={},
                          meta={'product': product,
                                'cookiejar': self.jar_counter})

    def parse_shipping_price1(self, response):
        product = response.meta['product']
        yield Request('http://www.sportsbikeshop.co.uk/motorcycle_parts/basket',
                      callback=self.parse_shipping_price2,
                      dont_filter=True,
                      meta={'product': product,
                            'cookiejar': response.meta['cookiejar']})

    def parse_shipping_price2(self, response):
        hxs = HtmlXPathSelector(response)
        product = response.meta['product']
        shipping_cost = hxs.select('//input[@name="delivery_method" and @checked="checked"]/../following-sibling::td/text()').extract()
        shipping_cost = shipping_cost[0].strip() if shipping_cost else '0'
        product['shipping_cost'] = extract_price(shipping_cost)
        yield product
