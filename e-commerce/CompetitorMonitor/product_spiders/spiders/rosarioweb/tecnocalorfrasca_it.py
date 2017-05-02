# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request

from product_spiders.items import Product, ProductLoader
from decimal import Decimal

import logging

class TecnocalorfrascaItSpider(BaseSpider):
    name = "tecnocalorfrasca.it"
    allowed_domains = ["tecnocalorfrasca.it"]
    start_urls = (
        'http://www.tecnocalorfrasca.it/',
        )

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        categories = hxs.select("//div[@id='pageColumnLeft']//span[@class='cat_link']/div/a/@href").extract()
        for category in categories:
            yield Request(category, callback=self.parse)

        pages = hxs.select("//div[@class='listingPageLinks']/span/a/@href").extract()
        for page in pages:
            yield Request(page, callback=self.parse)

        items = hxs.select("//div[@class='product_list']/div/a[@class='product_block_image']/@href").extract()
        for item in items:
            yield Request(item, callback=self.parse_item)

    def parse_item(self, response):
        url = response.url

        hxs = HtmlXPathSelector(response)
        name = hxs.select("//div[@id='pageContentSub']/div[@class='moduleBox']/\
                             div[@id='top_breadcrumb_link']/a[last()]/text()").extract()
        if not name:
            logging.error("NO NAME! %s" % url)
            return
        name = name[0]
                 
        # adding product
        price = hxs.select("//div[@id='pageContentSub']/form/div[@class='moduleBox']/\
                             div[@class='content']/div[@class='details']/ul/li[1]/span[2]/text()").re(u'€ (.*)')
        if not price:
            logging.error("NO PRICE! %s" % url)
            return
        price = price[0].replace(",", "")
        price_delivery = hxs.select("//div[@id='pageContentSub']/form/div[@class='moduleBox']/\
                             div[@class='content']/div[@class='details']/ul/li[2]/span[2]/text()").re(u'€ (.*)')
        if not price_delivery:
            logging.error("NO PRICE DELIVERY! %s" % url)
            return
        price_delivery = price_delivery[0].replace(",", "")
        price = Decimal(price) + Decimal(price_delivery)
 
        stock = hxs.select('//li[span[contains(text(), "Availability:")]]/span[@class="data"]/text()').re('(\d+)')
        stock = stock[0] if stock else '0'

        options = hxs.select('//table[@class="info_attribute_table"]/tr')
        if options:
            for option in options:
                l = ProductLoader(item=Product(), response=response)
                option_id = option.select('div/td/input/@value').extract()[0]
                l.add_value('identifier', response.url.split('/')[-1]+'-'+option_id)
                option_name = option.select('td/div/text()').extract()[0]
                l.add_value('name', name+' '+option_name)
                l.add_value('url', url)
                l.add_value('price', price)
                l.add_value('stock', stock)
                yield l.load_item()
        else:
            l = ProductLoader(item=Product(), response=response)
            l.add_value('identifier', response.url.split('/')[-1])
            l.add_value('name', name)
            l.add_value('url', url)
            l.add_value('price', price)
            l.add_value('stock', stock)
            yield l.load_item()
            
