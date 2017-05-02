import os
import csv
import xlrd

from scrapy.spider import BaseSpider
from scrapy.item import Item, Field
from scrapy.http import Request

from utils import extract_price_eu as extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from cStringIO import StringIO

HERE = os.path.abspath(os.path.dirname(__file__))


class BetterlifeHealthcareMeta(Item):
    cost_price = Field()

class BetterlifeHealthcareSpider(BaseSpider):
    name = 'betterlife_healthcare-betterlifehealthcare.com'

    filename = os.path.join(HERE, 'betterlife_healthcare_products.csv')
    start_urls = ('http://www.betterlifehealthcare.com/',)

    skus = []

    def __init__(self, *args, **kwargs):
        super(BetterlifeHealthcareSpider, self).__init__(*args, **kwargs)

    def start_requests(self):
        filename = os.path.join(HERE, 'MatchedProducts.xlsx')
        wb = xlrd.open_workbook(filename)
        sh = wb.sheet_by_index(0)

        for rownum in xrange(sh.nrows):
            if rownum < 1:
                continue

            row = sh.row(rownum)
            if row[0].value:
                self.skus.append(row[0].value.upper())

            yield Request(row[4].value, dont_filter=True, callback=self.parse_product, meta={'sku': row[0].value.upper()})

    def parse(self, response):
        categories = response.xpath('//ul[@class="categories"]//a/@href').extract()
        for category in categories:
            yield Request(response.urljoin(category))

        products = response.xpath('//a[@class="product_list_heading"]/@href').extract()
        for url in products:
            yield Request(response.urljoin(url), callback=self.parse_product)

        next_page = response.xpath('//div[@class="pagination_wrapper"]/a[contains(text(), "Next")]/@href').extract()
        if next_page:
            yield Request(response.urljoin(next_page[0]))

    def parse_product(self, response):
        name = response.xpath('//h1[@itemprop="name"]/text()').extract()[0].strip()
        image_url = response.xpath('//div[@class="products_image"]/img/@src').extract()
        image_url = image_url[0] if image_url else ''
        categories = response.xpath('//div[contains(@class, "breadcrumbs_wrapper")]//a/text()').extract()[1:]
        headers = response.xpath('//table[@class="variations_table"]//thead')[0].xpath('.//th/text()').extract()
        headers = [header.strip() for header in headers]
        options = response.xpath('//table[@class="variations_table"]//tr')
        for option in options:
            identifier = option.xpath('@id').extract()
            if not identifier:
                identifier = option.xpath('.//input[@name="varID"]/@value').extract()
            identifier = identifier

            if not identifier:
                continue

            identifier = identifier[0]

            values = option.xpath('.//td/text()').extract()
            option_name = name

            name_values = [header for header in headers if header not in ('Code', 'Catalogue Code', 'RRP',
                                                                          'Price', 'Buy')]
            for name_value in name_values:
                try:
                    value_index = headers.index(name_value)
                except ValueError:
                    value_index = None
                if value_index:
                    option_name_value = values[value_index].strip()
                    if option_name_value != '-':
                        option_name = option_name + ' ' + option_name_value

            code_index = headers.index('Code')
            sku = values[code_index]

            #if sku.upper() in self.skus:
            if sku.strip().upper() == response.meta['sku']:
                loader = ProductLoader(response=response, item=Product())
                loader.add_value('identifier', identifier)
                loader.add_value('sku', sku)
                loader.add_value('brand', '')
                loader.add_value('url', response.url)
                loader.add_value('category', categories)
                loader.add_value('name', option_name)
                price = option.xpath('.//span[@itemprop="price"]/text()').extract()
                if not price:
                    price = option.xpath(u'.//td/span[contains(@class, "var_tab_large") and not(span)]/text()').extract()
                if not price:
                    price = option.xpath(u'.//td/span[contains(@class, "var_tab_large")]/strong/text()').extract()
                if not price:
                    price = option.xpath(u'.//td/span/span[contains(@class, "var_tab_large")]/strong/text()').extract()

                if not price:
                    price = response.xpath('//div[@id="'+identifier+'"]//span[@itemprop="price"]/text()').extract()
                    if not price:
                        price = response.xpath('//div[@id="'+identifier+'"]//span[contains(@class, "var_tab_large")'
                                               'and not(span)]/text()').extract()
                    if not price:
                        price = response.xpath('//div[@id="'+identifier+'"]//span[contains(@class, "var_tab_large")]/'
                                               'strong/text()').extract()

                loader.add_value('price', round(extract_price(price[0]) / extract_price('1.20'), 2))
                if loader.get_output_value('price') < 35:
                    loader.add_value('shipping_cost', 3.95)

                loader.add_value('image_url', image_url)
                item = loader.load_item()

                yield item
