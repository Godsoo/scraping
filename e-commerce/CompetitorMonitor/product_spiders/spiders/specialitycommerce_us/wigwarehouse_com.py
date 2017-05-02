# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc
from urlparse import urlparse as urlparse
import itertools
import re
from scrapy.utils.url import add_or_replace_parameter


class WigwarehouseComSpider(BaseSpider):
    name = u'specialitycommerce_us-wigwarehouse.com'
    allowed_domains = ['wigwarehouse.com']
    start_urls = [
        'https://www.wigwarehouse.com'
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # categories
        for url in hxs.select('//*[@id="display_menu_1"]//td[@class="nav"]/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_categories)

    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        # products
        for url in hxs.select('//a[@class="productnamecolor colors_productname"]/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)
        # pages
        match = re.search("var SearchParams = '(.*?)';", response.body, re.DOTALL | re.IGNORECASE | re.MULTILINE)
        if match:
            pagination_params = match.group(1)
            pathname = urlparse(response.url).path
            b_url = urljoin_rfc(base_url, pathname) + '?' + pagination_params
            for page in hxs.select('//div[@class="pages_available_text"]//a/text()').extract():
                url = add_or_replace_parameter(b_url, 'page', page)
                yield Request(url, callback=self.parse_categories)
        else:
            self.log("ERROR: no pagination JS code {}".format(response.url))

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        product_name = hxs.select('//span[@itemprop="name"]/text()').extract()[0].strip()
        image_url = hxs.select('//*[@id="product_photo"]/@src').extract()
        if image_url:
            image_url = image_url[0].split('?')[0]
        else:
            image_url = ''
        identifier = hxs.select('//input[@name="ProductCode"]/@value').extract()[0]
        price = hxs.select('//span[@itemprop="price"]/text()').extract()[0]
        price = extract_price(price)
        category = hxs.select('//td[@class="vCSS_breadcrumb_td"]//a/text()').extract()[1:]
        brand = hxs.select('//meta[@itemprop="manufacturer"]/@content').extract()
        brand = brand[0] if brand else ''
        sku = identifier
        options = hxs.select('//*[@id="options_table"]//select')
        if len(options) == 3:
            color_variations = []
            for color in options[0].select('./option'):
                color_id = color.select('./@value').extract()[0]
                color_name = color.select('./text()').extract()[0]
                color_variations.append([color_id, color_name])
            size_variations = []
            for size in options[1].select('./option'):
                size_id = size.select('./@value').extract()[0]
                size_name = size.select('./text()').extract()[0]
                size_variations.append([size_id, size_name])
            type_variations = []
            for vtype in options[2].select('./option'):
                vtype_id = vtype.select('./@value').extract()[0]
                vtype_name = vtype.select('./text()').extract()[0]
                type_variations.append([vtype_id, vtype_name])
            options = itertools.product(color_variations, size_variations, type_variations)
            for option in options:
                product_identifier = identifier + '_'+option[0][0] + '_' + option[1][0] + '_' + option[2][0]
                size_name = option[0][1]
                if size_name == 'One Size':
                    size_name = ' '
                else:
                    size_name = ' ' + size_name + ' '
                name = product_name + size_name + option[1][1] + ' ' + option[2][1]
                loader = ProductLoader(item=Product(), selector=hxs)
                loader.add_value('identifier', product_identifier)
                loader.add_value('sku', sku)
                loader.add_value('url', response.url)
                loader.add_value('name', name)
                loader.add_value('price', price)
                opt_img = hxs.select('//*[@id="optionimg_' + option[0][0] + '"]/@src').extract()
                if not opt_img:
                    opt_img = hxs.select('//*[@id="optionimg_' + option[1][0] + '"]/@src').extract()
                if not opt_img:
                    opt_img = hxs.select('//*[@id="optionimg_' + option[2][0] + '"]/@src').extract()
                if opt_img:
                    image_url = opt_img[0].replace('S.jpg', 'T.jpg').split('?')[0]
                loader.add_value('image_url', urljoin_rfc(base_url, image_url))
                loader.add_value('category', category)
                loader.add_value('brand', brand)
                yield loader.load_item()
        if len(options) == 2:
            color_variations = []
            for color in options[0].select('./option'):
                color_id = color.select('./@value').extract()[0]
                color_name = color.select('./text()').extract()[0]
                color_variations.append([color_id, color_name])
            size_variations = []
            for size in options[1].select('./option'):
                size_id = size.select('./@value').extract()[0]
                size_name = size.select('./text()').extract()[0]
                size_variations.append([size_id, size_name])
            options = itertools.product(color_variations, size_variations)
            for option in options:
                product_identifier = identifier + '_'+option[0][0] + '_' + option[1][0]
                size_name = option[0][1]
                if size_name == 'One Size':
                    size_name = ' '
                else:
                    size_name = ' ' + size_name + ' '
                name = product_name + size_name + option[1][1]
                loader = ProductLoader(item=Product(), selector=hxs)
                loader.add_value('identifier', product_identifier)
                loader.add_value('sku', sku)
                loader.add_value('url', response.url)
                loader.add_value('name', name)
                loader.add_value('price', price)
                opt_img = hxs.select('//*[@id="optionimg_' + option[0][0] + '"]/@src').extract()
                if not opt_img:
                    opt_img = hxs.select('//*[@id="optionimg_' + option[1][0] + '"]/@src').extract()
                if opt_img:
                    image_url = opt_img[0].replace('S.jpg', 'T.jpg').split('?')[0]
                loader.add_value('image_url', urljoin_rfc(base_url, image_url))
                loader.add_value('category', category)
                loader.add_value('brand', brand)
                yield loader.load_item()
        elif len(options) == 1:
            for opt in options[0].select('./option'):
                opt_id = opt.select('./@value').extract()[0]
                opt_name = opt.select('./text()').extract()[0]
                if opt_name == 'One Size' or opt_name == 'One Set':
                    opt_name = ''
                else:
                    opt_name = ' ' + opt_name
                name = product_name + opt_name
                product_identifier = identifier + '_' + opt_id
                loader = ProductLoader(item=Product(), selector=hxs)
                loader.add_value('identifier', product_identifier)
                loader.add_value('sku', sku)
                loader.add_value('url', response.url)
                loader.add_value('name', name)
                loader.add_value('price', price)
                opt_img = hxs.select('//*[@id="optionimg_' + opt_id + '"]/@src').extract()
                if not opt_img:
                    opt_img = hxs.select('//*[@id="optionimg_' + opt_id + '"]/@src').extract()
                if opt_img:
                    image_url = opt_img[0].replace('S.jpg', 'T.jpg').split('?')[0]
                loader.add_value('image_url', urljoin_rfc(base_url, image_url))
                loader.add_value('category', category)
                loader.add_value('brand', brand)
                yield loader.load_item()
