# -*- coding: utf-8 -*-
"""
Customer: Powerhouse Fitness
Website: http://www.sweatband.com
Extract given URLs

Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5211

"""

import re
from powerhouseitems import PowerhouseFitnessMeta

from scrapy.spider import BaseSpider

from product_spiders.items import (Product, ProductLoaderWithNameStrip as ProductLoader)
from decimal import Decimal

class Sweatband(BaseSpider):
    name = 'powerhouse_fitness-sweatband.com'
    allowed_domains = ['sweatband.com']
    start_urls = ['http://www.sweatband.com/waterrower-classic-rowing-machine-with-s4-monitor.html#p=0i[199]',
                  'http://www.sweatband.com/waterrower-oxbridge-rowing-machine-with-s4-monitor.html#p=0i[199]',
                  'http://www.sweatband.com/waterrower-a1-home-rowing-machine.html#p=0i[199]',
                  'http://www.sweatband.com/waterrower-club-rowing-machine-with-s4-monitor.html#p=0i[199]',
                  'http://www.sweatband.com/waterrower-s1-rowing-machine-with-s4-monitor.html#p=0i[199]',
                  'http://www.sweatband.com/waterrower-m1-hirise-rowing-machine-with-s4-monitor.html#p=0i[199]',
                  'http://www.sweatband.com/waterrower-m1-lorise-rowing-machine-with-s4-monitor.html#p=0i[199]',
                  'http://www.sweatband.com/sole-e95-elliptical-cross-trainer.html',
                  'http://www.sweatband.com/sole-f63-treadmill.html',
                  'http://www.sweatband.com/sole-f85-treadmill.html',
                  'http://www.sweatband.com/sole-b94-upright-exercise-bike.html',
                  'http://www.sweatband.com/sole-e35-elliptical-cross-trainer.html',
                  'http://www.sweatband.com/sole-sb900-indoor-cycle.html',
                  'http://www.sweatband.com/sole-lcr-recumbent-exercise-bike.html',
                  'http://www.sweatband.com/sole-sb700-indoor-cycle.html',
                  'http://www.sweatband.com/sole-lcb-upright-exercise-bike.html']

    def parse(self, response):
        url = response.url

        l = ProductLoader(item=Product(), response=response)

        name = response.xpath('//h1[@itemprop="name"]/text()').extract()
        name = name[0].strip()
        l.add_value('name', name)

        price = response.xpath('//span[@itemprop="price"]/text()').extract()
        price = price[0] if price else 0
        l.add_value('price', price)

        identifier = response.xpath('//input[contains(@id, "hfProductId")]/@value').extract()
        l.add_value('identifier', identifier[0])

        categories = response.xpath('//div[@class="breadcrumbs"]//span[@itemprop]/text()').extract()[1:]
        l.add_value('category', categories)

        image_url = response.xpath('//meta[@property="og:image"]/@content').extract()
        l.add_value('image_url', image_url)
        l.add_value('url', url)
        brand = response.xpath( '//span[@id="brandname"]/text()').extract()
        brand = brand[0].strip() if brand else ''
        l.add_value('brand', brand)

        stock = response.xpath('//div[@class="item-availability"]/text()').re('in stock')
        if not stock:
            l.add_value('stock', 0)

        if l.get_output_value('price') < 15:
            l.add_value('shipping_cost', 1.50)

        item = l.load_item()
        discount_text = response.xpath('//div[contains(@id, "divVoucherBanner")]/div[@class="block-promo-title"]/text()').extract()
        if discount_text:
            discount_text = discount_text[0].strip()
            discount_percentage = re.findall('(\d+)%', discount_text)
            if discount_percentage:
                discount_percentage = int(discount_percentage[0])

            metadata = PowerhouseFitnessMeta()
            metadata['discount_text'] = discount_text
            metadata['discount_price'] = str(item['price'] - ((item['price'] * discount_percentage) / 100))
            item['metadata'] = metadata
        yield item


