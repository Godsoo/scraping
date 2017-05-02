# -*- coding: utf-8 -*-
"""
Customer: Specsavers NO
Website: http://www.lensit.no
Extract all products except the products in this category http://screencast.com/t/YAUozycmZnv

Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4724-specsavers-no-|-www-lensit-no-|-new-spider/details#

"""

import re
import json
from copy import deepcopy

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import HtmlResponse, Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import add_or_replace_parameter, url_query_parameter
from urlparse import urljoin

from product_spiders.utils import extract_price_eu

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader



class Lensit(BaseSpider):
    name = "specsavers_no-lensit.no"
    allowed_domains = ["lensit.no"]
    start_urls = ['http://www.lensit.no']

    def parse(self, response):
        base_url = get_base_url(response)

        categories = response.xpath('//div[@id="Menu"]//a[not(contains(@href, "solbriller"))]/@href').extract()
        categories += response.xpath('//ul[@class="subCategoryList"]//a/@href').extract()
        for category in categories:
           yield Request(response.urljoin(category))

        products = response.xpath('//div[@class="ProductPromote"]/a/@href').extract()
        products += response.xpath('//div[@class="Product"]/a/@href').extract()
        products += response.xpath('//div[@class="WebFolderBody"]//table//a/@href').extract()
        for product in products:
            if 'solbriller' not in product.lower():
                yield Request(urljoin(base_url, product), callback=self.parse_product)

    def parse_product(self, response):
        base_url = get_base_url(response)

        name = response.xpath('//span[contains(@id, "uxProductName")]/text()').extract()[0]

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('name', name)
        loader.add_xpath('price', '//div[contains(@class, "product-view__total-price")]/@data-price')
        image_url = response.xpath('//img[contains(@id, "uxProductImage")]/@src').extract()
        if image_url:
            loader.add_value('image_url', image_url[0])
        loader.add_xpath('brand', '//tr[td[contains(text(), "Produsent")]]/td[not(contains(text(), "Produsent"))]/text()')
        category = response.xpath('//tr[td[contains(text(), "Linsetype")]]/td[not(contains(text(), "Linsetype"))]/text()').extract()
        loader.add_value('category', category)
        loader.add_value('url', response.url)

        identifier = re.findall("return '(\d+)';", response.body)
        if not identifier:
            identifier = re.findall("var productId = (\d+);", response.body)
        identifier = identifier[0]

        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)

        item = loader.load_item()

        options = response.xpath('//span[@class="HeaderMinPrices"]/text()').extract()
        options = options[0].split(' / ') if options else []
        if options and len(options)>1:
            for option in options:
                option_item = deepcopy(item)
                name = re.findall('(.*) linser per', option)[0]
                option_item['name'] += ' ' + name
                option_item['identifier'] += '-' + ''.join(name.split())
                option_item['sku'] = option_item['identifier']
                price = re.findall('kr (.*)', option)
                option_item['price'] = extract_price_eu(price[0])
                yield option_item

        else:
            price = response.xpath('//span[@class="HeaderMinPrices"]/text()').extract()
            if not price:
                price = response.xpath('//div[@class="DescriptionExtraAccessories"]//span[contains(text(), "Kr")]/text()').extract()
            if not price:
                price = response.xpath('//div[@class="DescriptionExtra"]//span[contains(text(), "Kr") or contains(text(), "kr")]/text()').extract()
            price = price[0].lower()
            price = re.findall('\d+', price.split('kr')[-1])[0]
            item['price'] = extract_price_eu(price)
            yield item

