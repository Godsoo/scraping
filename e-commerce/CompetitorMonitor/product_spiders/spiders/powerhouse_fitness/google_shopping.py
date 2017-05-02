# -*- coding: utf-8 -*-
"""
Customer: Powerhouse Fitness
Website: http://www.google.co.uk
Search using file "feed_for_google.csv", extract all sellers.
Extract Part Number (or GTIN is no part number) as SKU.
Extract additional metadata: discount text and discount price.

Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/5210
"""
import os
import csv
import re
from decimal import Decimal

from selenium.common.exceptions import NoSuchElementException

from product_spiders.base_spiders import GoogleShoppingBaseSpider

HERE = os.path.abspath(os.path.dirname(__file__))


class PowerhouseGoogleShoppingSpider(GoogleShoppingBaseSpider):
    name = 'powerhouse-googleshopping'
    allowed_domains = ['google.co.uk']

    start_urls = ['https://www.google.co.uk/shopping?hl=en']

    proxy_service_target_id = 264
    proxy_service_location = 'uk'

    GOOGLE_DOMAIN = 'google.co.uk'
    SHOPPING_URL = 'https://www.google.co.uk/shopping?hl=en'

    ACTIVE_BROWSERS = 10

    csv_file = 'feed_for_google.csv'

    part_number_as_sku = True
    gtin_as_sku = True

    exclude_sellers = [
        'Powerhouse Fitness',
        'eBay - powerhouse_fitness'
    ]

    pages_to_process = 10

    def search_iterator(self):
        with open(os.path.join(HERE, self.csv_file)) as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader, 1):
                search_string = row['brand']
                yield (search_string, None, None)

    def _scrape_osrow_additional(self, item, osrow):
        try:
            osrow.find_element_by_xpath(".//*[@class='_sbk']")
        except NoSuchElementException:
            return {}

        discount_text = osrow.find_element_by_xpath(".//*[@class='_wtk']/div").get_attribute('textContent')
        m = re.search("(\d*)%", discount_text)
        if m:
            discount_percentage = m.group(1)
            discount_price = Decimal(item['price']) - Decimal(item['price']) * (Decimal(discount_percentage) / 100)
        else:
            self.log("No discount percentage in discount text for product {} (url: {}): {}".format(
                item['identifier'], item['url'], discount_text.encode('utf-8')))
            discount_price = ''

        meta = {
            'discount_text': discount_text.encode('utf-8'),
            'discount_price': discount_price
        }
        self.log("Found meta for product {} (url: {}): {}".format(item['identifier'], item['url'], str(meta)))

        return {
            'metadata': meta
        }