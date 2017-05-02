"""
Account: Tiger Chef
Name: ckitchen.com
"""

import os
import csv
from scrapy import Spider, Request
from scrapy.utils.url import add_or_replace_parameter
from product_spiders.utils import extract_price
from product_spiders.items import Product
from product_spiders.lib.schema import SpiderSchema
from product_spiders.config import DATA_DIR
from tigerchefloader import TigerChefLoader as ProductLoader
from tigerchefitems import TigerChefMeta
from itertools import (
    combinations,
    product as iterproduct
)
from decimal import Decimal


class CKitchenSpider(Spider):
    name = 'ckitchen.com'
    allowed_domains = ['ckitchen.com']
    start_urls = ['https://www.ckitchen.com/commercial/']

    # Trying to limit the number of option combinations to 50
    # Because some products has a huge number of options
    limit_options_to = 50

    def start_requests(self):
        if hasattr(self, 'prev_crawl_id'):
            filename = os.path.join(DATA_DIR, '%s_products.csv' % self.prev_crawl_id)
            if os.path.exists(filename):
                with open(filename) as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        yield Request(row['url'], callback=self.parse_product)
        for url in self.start_urls:
            yield Request(url)

    def parse(self, response):
        cats = response.xpath('//h3/a/@href').extract()
        for cat in cats:
            yield Request(response.urljoin(cat))

        try:
            to, total = response.xpath('//div[contains(@class, "total-results")]/span/text()')\
                .re(r'\d+')[1:]
            if to < total:
                next_page = response.meta.get('page_no', 1) + 1
                yield Request(add_or_replace_parameter(response.url, 'page', str(next_page)),
                              meta={'page_no': next_page},
                              callback=self.parse_full)
        except:
            self.log('WARNING: Error trying next page in => %s' % response.url)

        products = response.xpath('//div[contains(@class, "products-grid")]//a[@itemprop="url"]/@href').extract()
        for product in products:
            yield Request(response.urljoin(product), callback=self.parse_product)

    def _parse_options(self, response, product):
        no_options = 0
        # A checkbox is like a group of options but with only one option into it.
        # The checkboxes can be checked or unchecked.
        checkboxes = response.xpath('//*[@id="options"]//input[@data-val-id and @type="checkbox"]')
        # Group of options with radio buttons into it, we can select only one of each group.
        # But always will be one of each group selected.
        radio_groups = response.xpath('//div[@class="input-group type-radio"]')
        # [[(<id>, <name>, <price_incr>), ...],
        # ...]
        check_options = []
        for checkbox in checkboxes:
            val_id = checkbox.xpath('@data-val-id').extract()[0]
            val_name = checkbox.xpath('@data-caption').extract()[0]
            val_price = extract_price(checkbox.xpath('@data-price-adjustment').extract()[0].replace(' ', ''))
            if not val_price:
                # Only options that change the price
                continue
            check_options.append([[val_id, val_name, val_price], ])
        radio_options = []
        for radios_cont in radio_groups:
            radios = radios_cont.xpath('.//input[@data-val-id]')
            radios_group = [['', '', '0']]  # Unselected ...
            for radio in radios:
                val_id = radio.xpath('@data-val-id').extract()[0]
                val_name = radio.xpath('@data-caption').extract()[0]
                val_price = extract_price(radio.xpath('@data-price-adjustment').extract()[0].replace(' ', ''))
                if not val_price:
                    continue
                radios_group.append([val_id, val_name, val_price])
            radio_options.append(radios_group)

        radios_product = []
        if radio_options:
            radios_product_iter = iterproduct(*radio_options)
            # Filter to keep only those which have at least one selected
            # The website is using radio buttons but always there is one of them which not increases the price
            i = 0
            for d in radios_product_iter:
                if any([s[0] != '' for s in d]):
                    i += 1
                    if i > self.limit_options_to:
                        break
                    radios_product.append(d)

        for options in radios_product:
            if no_options > self.limit_options_to:
                return
            new_item = Product(product)
            for option in options:
                if option[0] == '':
                    # Unselected
                    continue
                new_item['identifier'] += '-' + option[0]
                new_item['name'] += ', ' + option[1]
                new_item['price'] = Decimal(new_item['price']) + option[2]

            no_options += 1
            yield new_item

        for i in range(1, len(check_options) + 1):
            check_combs = combinations(check_options, i)
            for checkbox_comb in check_combs:
                if no_options > self.limit_options_to:
                    return
                """
                Example:

                If options are:
                [['one', 'One', '1.5'], ['two', 'Two', '2'], ['three', 'Three', '3']]

                Then the combination will be:
                [(['one', 'One', '1.5'],),
                 (['two', 'Two', '2'],),
                 (['three', 'Three', '3'],)]

                [(['one', 'One', '1.5'], ['two', 'Two', '2']),
                 (['one', 'One', '1.5'], ['three', 'Three', '3']),
                 (['two', 'Two', '2'], ['three', 'Three', '3'])]

                [(['one', 'One', '1.5'], ['two', 'Two', '2'], ['three', 'Three', '3'])]
                """
                new_item = Product(product)
                for checkbox_opts in checkbox_comb:
                    for check_opt in checkbox_opts:
                        new_item['identifier'] += '-' + check_opt[0]
                        new_item['name'] += ', ' + check_opt[1]
                        new_item['price'] = Decimal(new_item['price']) + check_opt[2]
                no_options += 1
                yield new_item

                for options in radios_product:
                    if no_options > self.limit_options_to:
                        return
                    new_new_item = new_item.copy()
                    for option in options:
                        if option[0] == '':
                            # Unselected
                            continue
                        new_new_item['identifier'] += '-' + option[0]
                        new_new_item['name'] += ', ' + option[1]
                        new_new_item['price'] = Decimal(new_new_item['price']) + option[2]
                    no_options += 1
                    yield new_new_item


    def parse_product(self, response):
        page_schema = SpiderSchema(response)
        product_data = page_schema.get_product()

        sku = product_data['sku']
        main_name = product_data['name']
        main_price = extract_price(product_data['offers']['properties']['price'].replace(' ', ''))
        brand = product_data['brand']
        image_url = product_data['image']
        category = [d['properties']['name'] for d in page_schema.data['items'][1]
                    ['properties']['itemListElement']][0]

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('name', main_name)
        loader.add_value('identifier', sku)
        loader.add_value('price', main_price)
        loader.add_value('sku', sku)
        loader.add_value('brand', brand)
        loader.add_value('category', category)
        loader.add_value('url', response.url)
        loader.add_value('image_url', image_url)

        description = ' '.join(response.xpath('//*[@class="product-details"]//text()').extract())
        sold_as = ''
        if 'Priced per' in description:
            sold_as = description.split('Priced per')[1]
        if 'Priced by' in description:
            sold_as = description.split('Priced by')[1]
        if 'Price per' in description:
            sold_as = description.split('Price per')[1]
        if ';' in sold_as:
            sold_as = sold_as.split(';')[0]
        if '.' in sold_as:
            sold_as = sold_as.split('.')[0]
        if ',' in sold_as:
            sold_as = sold_as.split(',')[0]

        if not sold_as:
            sold_as = 'each'

        product = loader.load_item()
        metadata = TigerChefMeta()
        metadata['sold_as'] = sold_as
        product['metadata'] = metadata

        yield product

        for option in self._parse_options(response, product):
            yield option
