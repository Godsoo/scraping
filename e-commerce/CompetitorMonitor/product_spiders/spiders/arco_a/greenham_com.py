# -*- coding: utf-8 -*-

import os.path
import csv

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price

HERE = os.path.abspath(os.path.dirname(__file__))
def parse_variant(string):
    variant = {}
    for pair in string.split(";"):
        keyval = pair.split("=")
        if len(keyval) > 1:
            variant[keyval[0]] = keyval[1]
    return variant

class GreenhamComSpider(BaseSpider):
    name = 'greenham.com'
    allowed_domains = ['greenham.com']
    start_urls = ('http://www.greenham.com/',)

    def __init__(self, *args, **kwargs):
        super(GreenhamComSpider, self).__init__(*args, **kwargs)

        self.codes = {}

        with open(os.path.join(HERE, 'competitors_codes.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.codes[row['url'].lower()] = row['code']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        categories_urls = hxs.select('//div[@id="nav_main"]//li[@class="Lc left_col"]//a/@href').extract()
        for url in categories_urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        products = hxs.select('//div[@class="prod_cols"]/div/h3/label/a/@href').extract()
        categories = hxs.select('//div[contains(@class, "subcat_item")]/div/a/@href').extract()
        for url in categories:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_category)
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)
        next = hxs.select('//ul[@class="pager"][1]/li/a[contains(text(), "Next Page")]/@href').extract()
        if next:
            yield Request(urljoin_rfc(base_url, next[0]), callback=self.parse_category)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('url', response.url)
        name = hxs.select('//div[@class="catBanner"]/h2/text()').extract()[0]
        price = hxs.select('//span[@id="variant-price-header"]/text()').extract()

        if price:
            price = extract_price(price[0])
        else:
            return

        sku = hxs.select('//div[@class="prod"]/p[@class="code"]').re("Code: ([0-9]+)")[0]
        brand = hxs.select('//td[@class="attrib" and text()="Manufacturer"]/following-sibling::td/text()').extract()

        product_loader.add_value('sku', sku)
        category = " ".join(hxs.select('//div[@id="breadcrumb"]/ul/li/a/text()').extract()[2:-1])[2:]
        product_loader.add_value('category', category)
        product_loader.add_value('brand', brand)
        image_url = hxs.select('//div[@id="primary_image"]/a/img/@src').extract()
        if image_url:
            product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        identifier = hxs.select('//input[@name="productCodePost"]/@value').extract()
        product = product_loader.load_item()
        variants = hxs.select('//select[@id="variant"]/option')
        if variants:
            for option in variants:
                value = option.select('./@value').extract()
                if value:
                    variant = parse_variant(value[0])
                    title = option.select('./text()').extract()[0]
                    price = extract_price(variant.get('price', "0"))
                    subid = variant.get('code')
                    if subid:
                        prod = Product(product)
                        prod['identifier'] = "%s_%s" % (identifier[0], subid)
                        prod['price'] = price
                        subname = title.split(u"£")
                        if subname:
                            subname = subname[0].strip().replace(u"\xa0", " ")
                            if subname.endswith(","):
                                subname = subname[:-1]
                        prod['name'] = "%s %s" % (name, subname)
                        yield prod
        else:
            # one option product
            prod = Product(product)
            prod['name'] = name 
            o = hxs.select('//div[@class="options_not_available"]/text()').extract()
            if o:
                prod['name'] += ' ' + o[0].strip()
            prod['identifier'] = identifier[0]
            prod['price'] = price

            yield prod
