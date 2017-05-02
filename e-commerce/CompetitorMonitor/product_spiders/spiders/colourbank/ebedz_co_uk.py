# -*- coding: utf-8 -*-
from decimal import Decimal

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import HtmlResponse, Request, FormRequest
from scrapy.utils.response import get_base_url
from urlparse import urljoin
from decimal import Decimal
from product_spiders.utils import fix_spaces, extract_price2uk
import re, json, itertools
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class EBedzCoUK(BaseSpider):
    name = "ebedz.co.uk"
    allowed_domains = ["ebedz.co.uk"]
    start_urls = ["http://www.ebedz.co.uk/"]

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        category_urls = hxs.select('//div[@class="parentMenu"]/a/@href').extract()
        for url in category_urls:
            yield Request(url, callback=self.parse_category)
            
    def parse_category(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        next_page_url = hxs.select('//ul[@class="pagination"]//a[text()=">"]/@href').extract()
        if next_page_url:
            yield Request(next_page_url[0], callback=self.parse_category)

        subcategory_urls = [] # hxs.select('//div[@class="category-info"]//a/@href').extract()
        for url in subcategory_urls:
            yield Request(urljoin(base_url, url), callback=self.parse_category)

        product_urls = hxs.select('//div[@class="name"]/a/@href').extract()
        for url in product_urls:
            yield Request(url, callback=self.parse_product)

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        name = hxs.select('//h1/text()').extract()
        if not name:
            return
        else:
            name = name[0]
        identifier = hxs.select('//input[@name="product_id"]/@value').extract()[0]
        price = hxs.select('//div[@class="price"]/div[@id="myoc-lpu"]/text()').extract()
        if price:
            price = extract_price2uk(price[0])
            stock = 1
        else:
            price = Decimal(0)
            stock = 0

        loader = ProductLoader(selector=hxs, item=Product())
        loader.add_value('name', name)
        loader.add_value('price', price)
        loader.add_value('stock', stock)
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        loader.add_xpath('image_url', '//a[@class="thumbnail"]/img/@src')
        loader.add_value('url', response.url)
        loader.add_value('shipping_cost', 0)
        for category in hxs.select('//ul[@class="breadcrumb"]/li/a/text()')[:-1].extract():
            loader.add_value('category', category)
        loader.add_xpath('brand', '//li[contains(text(), "Brand")]/a/text()')
        product = loader.load_item()

        option_boxes = hxs.select('//select[@class="form-control" and contains(@id, "option")\
                        and not(contains(./option/., "V.A.T."))\
                        and not(contains(./option/., "VAT"))\
                        and not(contains(./option/., "Delivery"))]')
        if not option_boxes:
            yield product
            return

        options_dict = dict()
        options = []
        for option_box in option_boxes:
            option_group = []
            for option in option_box.select('./option[@value!="" and not(contains(.,"VAT Exempt"))]'):
                option_id = option.select('./@value')[0].extract()
                option_name = option.select('./text()')[0].extract()
                option_price = re.search(u'\(\+\xa3(.*)\)', option_name)
                option_price = Decimal(option_price.group(1)) if option_price else Decimal('0.00')

                option_name = re.sub('VAT Payable ?-? ?','', option_name)
                option_name = re.sub(u'\(\+\xa3(.*)\)', '', option_name).strip()
                options_dict[option_id] = {'name': option_name, 'price': option_price}
                option_group.append(option_id)
            options.append(option_group)

        options = itertools.product(*options)

        for option in options:
            option_name = ' '.join([options_dict[option_id]['name'] for option_id in option])
            option_price = sum([options_dict[option_id]['price'] for option_id in option])
            option = sorted(option)
            option_identifier = '-'.join(option)
            product['identifier'] = '-'.join((identifier, option_identifier))
            product['price'] = price + option_price
            product['name'] = fix_spaces(' '.join((name, option_name)))
            yield product
