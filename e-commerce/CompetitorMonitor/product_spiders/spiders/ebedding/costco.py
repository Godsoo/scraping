# -*- coding: utf-8 -*-
"""
Customer: E-Bedding
Website: http://www.sweatband.com
Extract all products and product options from the following sub categories http://screencast.com/t/wB83XQsrKh0Y

Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5191

"""

import re
import itertools

from copy import deepcopy
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import HtmlResponse, Request, FormRequest
from scrapy.utils.response import get_base_url
from urlparse import urljoin
from product_spiders.utils import extract_price, fix_spaces

from scrapy import log

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader


class CostcoSpider(BaseSpider):
    name = "ebedding-costco.co.uk"
    allowed_domains = ["costco.co.uk"]
    start_urls = ["http://www.costco.co.uk/view/c/furniture-home/furniture/beds-mattresses-headboards",
                  "http://www.costco.co.uk/view/c/furniture-home/home-furnishings"]

    handle_httpstatus_list = [500]

    def parse(self, response):
        pages = response.xpath('//a[@class="pagination_next"]/@href').extract()
        for page in pages:
            yield Request(response.urljoin(page))

        product_urls = response.xpath('//div[@class="productList_name"]/a/@href').extract()
        for url in product_urls:
            yield Request(response.urljoin(url), callback=self.parse_product)

        categories = response.xpath('//ul[contains(@class, "catPromos")]//a/@href').extract()
        for category in categories:
            yield Request(response.urljoin(category))

    def parse_product(self, response):

        ignore_options = response.meta.get('ignore_options', False)

        if not ignore_options:
            formdata = {}
            form_inputs = response.xpath('//form[@id="productFormBean"]/input')
            for form_input in form_inputs:
                formdata[form_input.xpath('@name').extract()[0]] = form_input.xpath('@value').extract_first()

            option_elements = []

            option_selects = response.xpath('//select[contains(@name, "attributes[")]')
            for option_select in option_selects:
                option_element = []
                attribute_name = option_select.xpath('@name').extract()[0]
                for option in option_select.xpath('option'):
                    option_value = option.xpath('@value').extract()[0]
                    option_element.append({attribute_name: option_value})
                if option_element:
                    option_elements.append(option_element)

            colours_data = []
            colours = response.xpath('//a[contains(@class, "swatchclr")]/@name').extract()
            for colour in colours:
                colours_data.append({"attributes['colour']": colour})
            if colours_data:
                option_elements.append(colours_data)

            if option_elements:
                options = itertools.product(*option_elements)
                for option in options:
                    option_formdata = deepcopy(formdata)
                    for attribute in option:
                        option_formdata.update(attribute)
                    option_formdata['variantType'] = 'change'

                    option_url = 'http://www.costco.co.uk/view/component/QuickliveProductDetailsComponentController'

                    yield FormRequest(option_url, formdata=option_formdata, dont_filter=True,
                                      callback=self.parse_product, meta={'ignore_options': True, 'url': response.url})

        loader = ProductLoader(response=response, item=Product())
        name = response.xpath('//h1[@itemprop="name"]/text()').extract()[0].strip()
        name = fix_spaces(name)
        loader.add_value('name', name)
        loader.add_value('url', response.url)

        price = response.xpath('//div[@id="inclprice"]/span[@class="vat_price"]/text()').extract()
        price = extract_price(price[0]) if price else '0'
        loader.add_value('price', price)

        img_url = response.xpath('//meta[@property="og:image"]/@content').extract()
        if img_url:
            loader.add_value('image_url', response.urljoin(img_url[0]))

        categories = response.xpath('//ul[contains(@class, "breadcrumbs")]/li/a/text()').extract()[-3:]
        loader.add_value('category', categories)
        brand = response.xpath('//div[contains(@id, "productDetail_product_specification")]//li[contains(text(), "Brand: ")]/text()').extract()
        brand = re.findall('Brand: (.*)', ' '.join(brand[0].split())) if brand else ''
        loader.add_value('brand', brand)

        identifier = response.xpath('//input[@name="productCode"]/@value').extract()
        if not identifier:
            log.msg('ERROR >>> Product without identifier: ' + response.url)
            return
        loader.add_value('identifier', identifier[0])
        loader.add_value('sku', identifier[0])

        out_of_stock = response.xpath('//div[@class="add_to_bag"]/span[@class="placeholder" and contains(text(), "Out of stock")]')
        if out_of_stock:
            loader.add_value('stock', 0)

        yield loader.load_item()
