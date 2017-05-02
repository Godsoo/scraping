# -*- coding: utf-8 -*-
import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price


class ProtecdirectCoUkSpider(BaseSpider):
    name = 'protecdirect.co.uk'
    allowed_domains = ['protecdirect.co.uk']
    start_urls = ('http://www.protecdirect.co.uk/',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # check for new categories
        categories_urls = hxs.select('//*[@id="nav_main"]//a/@href').extract()
        for url in categories_urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_categories)

    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        # lookup for subcategories
        categories_urls = hxs.select('//div[@class="nav_column"]/div[2]//div[@class="allFacetValues"]//a/@href').extract()
        for url in categories_urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_categories)

        # pagination
        pages_urls = hxs.select('//ul[@class="pager"]//a/@href').extract()
        for url in pages_urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_categories)

        # parse products list
        try:
            category = hxs.select('//div[@id="breadcrumb"]//li[last()]/a/text()')\
                .extract()[0].replace('>', '').replace('Category: ', '').replace('Brand: ', '').strip()
        except:
            category = ''


        sizes = {'-Small': 'S', '-Medium': '-M', '-Large': '-L', '-Extra Large': 'XL', '-Extra Extra Large': 'XXL'}
        products = hxs.select('//div[contains(@class,"subcat_column-item")]')
        for product in products:
            product_loader = ProductLoader(item=Product(), selector=hxs)
            product_loader.add_value('category', category)
            brand = product.select('.//h3[@class="productName"]/span/a/text()').extract()
            brand = brand[0] if brand else ''
            product_loader.add_value('brand', brand)
            product_name = product.select('.//h3[@class="productName"]//a/text()').extract()[-1]

            brand_in_name = False
            for w in re.findall('([a-zA-Z]+)', product_name):
                if w.upper() in brand.upper():
                    brand_in_name = True

            if brand.upper() not in product_name.upper() and not brand_in_name:
                product_name = brand + ' ' + product_name

            url = product.select('.//h3[@class="productName"]//a/@href').extract()[-1]
            product_loader.add_value('url', urljoin_rfc(base_url, url))
            image_url = product.select('.//div[@class="img"]//img/@src').extract()[0]
            product_loader.add_value('image_url', urljoin_rfc(base_url, image_url))
            # check if this product contains multiple options:
            options = product.select('.//select[contains(@id,"variant")]//option')
            if options:
                for option in options:
                    prod = product_loader.load_item()
                    value = option.select('./@value').extract()[0]
                    parts = value.split(';')
                    product_options = {}
                    for part in parts:
                        params = part.split('=')
                        if len(params) != 2:
                            continue
                        product_options[params[0]] = params[1]
                    name = option.select('.//text()').extract()[0]
                    name = product_name + ' ' + name
                    prod['name'] = name
                     
                    identifier = product_options.get('code')
                    
                    for size in sizes:
                        identifier = identifier.replace(size, sizes[size])

                    prod['identifier'] = identifier
                    prod['sku'] = identifier#product_options.get('code')
                    prod['price'] = extract_price(product_options.get('price'))
                    if prod['price'] < 25:
                        prod['shipping_cost'] = '4.95'
                    yield prod
            else:
                # no options
                product_loader.add_value('name', product_name)
                identifier = product.select('.//div[@class="code"]/text()').extract()[0].strip().replace('Code: ', '')
                product_loader.add_value('identifier', identifier)
                product_loader.add_value('sku', identifier)
                price = product.select('.//div[@class="cart"]//span[@class="price"]/text()').extract()[0].strip()
                product_loader.add_value('price', extract_price(price))
                if product_loader.get_output_value('price') < 25:
                    product_loader.add_value('shipping_cost', '4.95')
                product = product_loader.load_item()
                yield product
