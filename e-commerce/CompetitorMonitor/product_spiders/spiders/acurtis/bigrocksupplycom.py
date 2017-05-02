import re
import json
import itertools
from decimal import Decimal

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request

from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.utils import extract_price

from product_spiders.items import Product, ProductLoader

import logging


class BigrocksupplyComSpider(BaseSpider):
    name = "bigrocksupply.com"
    allowed_domains = ["bigrocksupply.com"]
    start_urls = (
        'http://www.bigrocksupply.com/Roof-Drains.html',
        'http://www.bigrocksupply.com/Pipe-Penetrations.html',
        'http://www.bigrocksupply.com/Mechanical-Supports.html',
        )

    download_delay = 3

    def start_requests(self):
        brands_url = "http://www.bigrocksupply.com/store/Search.aspx?SearchTerms=%25"
        yield Request(brands_url, callback=self.parse_brands)

    def parse_brands(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        brands = hxs.select('//table[@id="dlManufacturers"]//a/text()').extract()
        brands = map(lambda brand: brand.strip(), brands)
        for url in self.start_urls:
            yield Request(url, callback=self.parse_categories, meta={'brands':brands})

    def parse_categories(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        meta = response.meta

        subcategories = hxs.select('//div[@class="CategoryChildCategories"]/div[@class="CategoryCategoryLink"]/a/@href').extract()
        if subcategories:
            for subcat in subcategories:
                subcat_url = urljoin_rfc(base_url, subcat)
                yield Request(subcat_url, callback=self.parse_categories, meta=meta)

        pages = hxs.select(
            "//ul[contains(@class, 'pagination')]//a/@href"
        ).extract()
        for page in pages:
            yield Request(urljoin_rfc(base_url, page), callback=self.parse_categories, meta=meta)

        items = hxs.select('//div[@class="product-list"]//div[@class="no-m-b"]/a/@href').extract()
        for item in set(items):
            yield Request(
                urljoin_rfc(base_url, item),
                callback=self.parse_item,
                meta=meta
            )

    def parse_item(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        meta = response.meta

        name = hxs.select(
            '//div[@class="page-header"]/h1/text()'
        ).extract()
        if not name:
            logging.error("No product name! %s" % response.url)
            return
        name = name[0]

        url = response.url

        price = hxs.select('//*[@itemprop="price"]//text()').re(r'([\d.,]+)')
        if not price:
            logging.error("No product price! %s %s" % (name, response.url))
            return
        price = price[0]
        price = Decimal(price)

        product_id = hxs.select('//input[@id="hfItemID"]/@value').extract()
        if not product_id:
            self.log("ERROR product_id not found")
            return
        else:
            product_id = product_id[0]

        image_url = hxs.select('//*[@itemprop="image"]//img/@src').extract()
        image_url = urljoin_rfc(base_url, image_url[0]) if image_url else ''

        category = hxs.select('//span[@id="lblCategoryTrail"]/a/text()').extract()[-1]

        sku = hxs.select('//small[contains(text(), "Item #")]/text()').re(r'Item #(.*)')

        brand = ''
        for b in meta.get('brands'):
            if b.upper() in name.upper():
                brand = b
                break

        options = self.get_options(response, price)
        if options:
            # adding products variations from options
            for option in options:
                l = ProductLoader(item=Product(), response=response)
                # l.add_value('identifier', str(item_name))
                l.add_value('identifier', product_id + ' ' + ' '.join(option[0]))
                l.add_value('name', name + ' ' + option[1])
                l.add_value('url', url)
                l.add_value('brand', brand)
                l.add_value('image_url', image_url)
                l.add_value('category', category)
                item = l.load_item()
                params = {'itemID': int(product_id),
                          'personalizationIds': [],
                          'personalizationStrings': [],
                          'quantity': 1,
                          'variantIDs': map(int, option[0])}

                price_url = 'http://www.bigrocksupply.com/Store/Controls/ScriptService.asmx/GetPrice'
                req = Request(price_url,
                              method='POST',
                              dont_filter=True,
                              body=str(params),
                              headers={'Content-Type':'application/json'},
                              callback=self.parse_price,
                              meta={'item':item})
                yield req
        else:
            # adding one product
            l = ProductLoader(item=Product(), response=response)
            # l.add_value('identifier', str(name))
            l.add_value('identifier', product_id)
            l.add_value('name', name)
            l.add_value('url', url)
            l.add_value('brand', brand)
            l.add_value('price', price)
            l.add_value('image_url', image_url)
            l.add_value('category', category)
            l.add_value('sku', sku)
            yield l.load_item()

    def parse_price(self, response):
        item = response.meta.get('item')
        result = json.loads(response.body).get('d')
        item['price'] = extract_price(result.get('price'))
        in_stock = 'IN STOCK' == result.get('status').upper()
        if not in_stock:
            item['stock'] = 0
        item['sku'] = result.get('itemNr')
        yield item

    def get_options(self, response, base_price):
        hxs = HtmlXPathSelector(response)
        options = []
        options_containers = hxs.select("//div[@id='dvProductVariations']//select")

        combined_options = []
        for options_container in options_containers:
            element_options = []
            for option in options_container.select('option[@value!="-999"]'):
                option_id = option.select('@value').extract()[0]
                option_split = option.select('text()').extract()[0].split(' / ')
                option_desc = option_split[0]
                element_options.append((option_id, option_desc))
            combined_options.append(element_options)

        combined_options = list(itertools.product(*combined_options))
        for combined_option in combined_options:
            name, option_ids = '', []
            for option in combined_option:
                option_ids.append(option[0])
                name = name + ' - ' + option[1]
                options.append((option_ids, name))
        return options
