# -*- coding: utf-8 -*-
import json
import urlparse

import re
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price_eu, extract_price


class BedandmattressSpider(BaseSpider):
    name = 'bedandmattress'
    allowed_domains = ['www.bedandmattress.co.uk']
    start_urls = [
        'http://www.bedandmattress.co.uk/',
        # 'http://www.bedandmattress.co.uk/Sweet_Dreams_Romola-321',
        # 'http://www.bedandmattress.co.uk/Sleepeezee_Memory_Comfort_800-403'
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        # we extract the categories urls
        categories = hxs.select("//li[@class='uk-parent']//@href").extract()
        for category in categories:
            self.log("category: {}".format(category))
            yield Request(
                urlparse.urljoin(response.url, category),
                callback=self.parse_category
            )

    def parse_category(self, response):
        """
        While parsing a category page we need to look after a product or category list
        """
        hxs = HtmlXPathSelector(response)

        # products
        for product_url in hxs.select("//a[@class='uk-button uk-button-mini uk-button-success']//@href").extract():
            self.log("product: {} scraped from {}".format(product_url, response.url))
            yield Request(
                urlparse.urljoin(get_base_url(response), product_url),
                callback=self.parse_product
            )

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        # loader = ProductLoader(item=Product(), response=response)
        product_name = hxs.select("//div[@class='uk-container']//h1//text()").extract()
        if product_name:
            product_name = product_name[0]

        for sub_option in hxs.select("//table[@class='prices']//tr"):
            loader = ProductLoader(item=Product(), response=response)

            price = ''.join(sub_option.select("./td[2]/p/text()").extract())
            price = extract_price(price)

            loader.add_value('price', price)
            loader.add_value('url', response.url)

            option_name = sub_option.select("./td[1]//text()").extract()
            if option_name:
                option_name = option_name[0]

            loader.add_value('name', "{product} {option}".format(
                product=product_name,
                option=option_name
            ))

            if price:
                loader.add_value('stock', '1')
            else:
                loader.add_value('stock', '0')
            loader.add_xpath('category', "//ul[@class='uk-breadcrumb']//li[1 < position() and position() < last()]//text()")
            loader.add_xpath('brand', "//h4[@class='man']//text()")
            shipping_cost = '0'
            loader.add_value('shipping_cost', shipping_cost)

            identifier = sub_option.select("./td[3]/a/@href").extract()
            if identifier:
                loader.add_value('sku', identifier[0].split("=")[-1])
                loader.add_value('identifier', identifier[0].split("=")[-1])
            else:
                loader.add_value('sku', response.url.split("/")[-1] + option_name)
                loader.add_value('identifier', response.url.split("/")[-1] + option_name)

            img_href = hxs.select("//img[@class='main_image']//@src").extract()
            if img_href:
                loader.add_value('image_url', urlparse.urljoin(get_base_url(response), img_href[0]))
            yield loader.load_item()

        # for beds

        options_js = ''.join(hxs.select("//script[contains(., 'list')]/text()").extract())

        if options_js:

            lists = options_js.split("var lists = new Array();")[-1]

            lists = lists.replace("lists['", '"')
            lists = lists.replace("'] = new Array(", '": ')
            lists = lists.replace(');', ',')
            lists = lists.strip()
            lists = '{' + lists[:-1] + '}'
            lists_json = json.loads(lists)

            for size_index, size in enumerate(lists_json['sizes']):

                if 'bases' in lists_json:
                    for base_index, base in enumerate(lists_json['bases'][size_index]):
                        for colour_index, colour in enumerate(lists_json['cols'][size_index][base_index]):
                            if 'firms' in lists_json:
                                for firm_indes, firm in enumerate(lists_json['firms'][size_index][base_index][colour_index]):
                                    loader = ProductLoader(item=Product(), response=response)
                                    price = extract_price(lists_json['prices'][size_index][base_index][colour_index][firm_indes])
                                    loader.add_value('price', price)
                                    loader.add_value('name', "{product} {size} {base} {colour} {firm}".format(
                                        product=product_name,
                                        size=size,
                                        base=base,
                                        colour=colour,
                                        firm=firm
                                    ))
                                    loader.add_value('sku', lists_json['ids'][size_index][base_index][colour_index][firm_indes])
                                    loader.add_value('identifier', lists_json['ids'][size_index][base_index][colour_index][firm_indes])
                                    loader.add_value('url', response.url)
                                    if price:
                                        loader.add_value('stock', '1')
                                    else:
                                        loader.add_value('stock', '0')
                                    loader.add_xpath('category', "//ul[@class='uk-breadcrumb']//li[1 < position() and position() < last()]//text()")
                                    loader.add_xpath('brand', "//h4[@class='man']//text()")
                                    shipping_cost = '0'
                                    loader.add_value('shipping_cost', shipping_cost)

                                    img_href = hxs.select("//img[@class='main_image']//@src").extract()
                                    if img_href:
                                        loader.add_value('image_url', urlparse.urljoin(get_base_url(response), img_href[0]))
                                    yield loader.load_item()
                            else:
                                loader = ProductLoader(item=Product(), response=response)
                                price = extract_price(lists_json['prices'][size_index][base_index][colour_index])
                                loader.add_value('price', price)
                                loader.add_value('name', "{product} {size} {base} {colour}".format(
                                    product=product_name,
                                    size=size,
                                    base=base,
                                    colour=colour
                                ))
                                loader.add_value('sku', lists_json['ids'][size_index][base_index][colour_index])
                                loader.add_value('identifier', lists_json['ids'][size_index][base_index][colour_index])
                                loader.add_value('url', response.url)
                                if price:
                                    loader.add_value('stock', '1')
                                else:
                                    loader.add_value('stock', '0')
                                loader.add_xpath('category', "//ul[@class='uk-breadcrumb']//li[1 < position() and position() < last()]//text()")
                                loader.add_xpath('brand', "//h4[@class='man']//text()")
                                shipping_cost = '0'
                                loader.add_value('shipping_cost', shipping_cost)

                                img_href = hxs.select("//img[@class='main_image']//@src").extract()
                                if img_href:
                                    loader.add_value('image_url', urlparse.urljoin(get_base_url(response), img_href[0]))
                                yield loader.load_item()
                else:
                    for colour_index, colour in enumerate(lists_json['cols'][size_index]):
                        loader = ProductLoader(item=Product(), response=response)
                        price = extract_price(lists_json['prices'][size_index][colour_index])
                        loader.add_value('price', price)

                        loader.add_value('name', "{product} {size} {colour}".format(
                            product=product_name,
                            size=size,
                            colour=colour
                        ))
                        loader.add_value('sku', lists_json['ids'][size_index][colour_index])
                        loader.add_value('identifier', lists_json['ids'][size_index][colour_index])

                        loader.add_value('url', response.url)
                        if price:
                            loader.add_value('stock', '1')
                        else:
                            loader.add_value('stock', '0')
                        loader.add_xpath('category', "//ul[@class='uk-breadcrumb']//li[1 < position() and position() < last()]//text()")
                        loader.add_xpath('brand', "//h4[@class='man']//text()")
                        shipping_cost = '0'
                        loader.add_value('shipping_cost', shipping_cost)

                        img_href = hxs.select("//img[@class='main_image']//@src").extract()
                        if img_href:
                            loader.add_value('image_url', urlparse.urljoin(get_base_url(response), img_href[0]))
                        yield loader.load_item()
