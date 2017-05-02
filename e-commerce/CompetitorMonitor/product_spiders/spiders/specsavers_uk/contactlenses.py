# -*- coding: utf-8 -*-
"""
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4549

There are also Discontinued products but we don't scrape them as they don't have identifier.
"""
import re
from urlparse import urljoin

from scrapy import Spider, Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import url_query_parameter

from product_spiders.items import ProductLoaderWithNameStrip, Product


class ContactLenses(Spider):
    name = 'specsavers_uk-contact_lenses'
    allowed_domains = ('contactlenses.co.uk', )

    start_urls = ['http://www.contactlenses.co.uk/']

    def parse(self, response):
        for cat_url in response.xpath("//div[@id='catalog']//li/a/@href").extract():
            url = urljoin(get_base_url(response), cat_url)
            yield Request(url, callback=self.parse_category)

    def parse_category(self, response):
        for prod_url in response.xpath("//table[@id='products']/tr/td//a[img]/@href").extract():
            url = urljoin(get_base_url(response), prod_url)
            yield Request(url, callback=self.parse_product)

    def parse_product(self, response):
        name = response.xpath("//h2/span[@itemprop='name']/text()").extract()
        if not name:
            name = response.xpath("//table//tr/td//h2/text()").extract()
        name = name[0]
        price = response.xpath("//span[@itemprop='price']/text()").re('[\d\.]+')
        if not price:
            price = response.xpath("//span[@class='pr-price']/strong/text()").re('[\d\.]+')
        price = price[0]
        stock = response.xpath("//*[@itemprop='availability']/@href").extract()
        if stock:
            if 'InStock' in stock[0]:
                stock = None
            else:
                stock = 0
        else:
            stock = None

        cats = response.xpath("//div[@class='grid_10']/h1/a/text()").extract()
        brand = cats[-1]
        image_url = response.xpath("//img[@alt='{}']/@src".format(name)).extract()
        m = re.search("details(.*)\.html", response.url)
        if m:
            identifier = m.group(1)
        else:
            entryid = url_query_parameter(response.url, 'entryid')
            priceid = url_query_parameter(response.url, 'priceid')
            if not entryid or not priceid:
                raise KeyError("Not found entryid and priceid in url: {}".format(response.url))
            identifier = entryid + priceid
        sku = identifier

        loader = ProductLoaderWithNameStrip(Product(), response=response)

        loader.add_value('name', name)
        loader.add_value('price', price)
        loader.add_value('stock', stock)
        loader.add_value('url', response.url)
        loader.add_value('brand', brand)
        loader.add_value('sku', sku)
        loader.add_value('identifier', identifier)
        loader.add_value('image_url', image_url)
        loader.add_value('category', cats)

        yield loader.load_item()