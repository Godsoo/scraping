# -*- coding: utf-8 -*-
import os
import csv

from scrapy.spider import BaseSpider
from scrapy.http import HtmlResponse, Request, FormRequest

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader

here = os.path.abspath(os.path.dirname(__file__))


class Alltomlinser(BaseSpider):
    name = "specsavers_sw-alltomlinser.se"
    allowed_domains = ["alltomlinser.se"]
    start_urls = ['http://www.alltomlinser.se']

    rotate_agent = True

    def start_requests(self):
        search_url = ('http://www.alltomlinser.se/default.asp?page=1&sort=sTotalPrice&sPart=1'
                      '&drlType=&txtSearch=%s&drlBrand=&drlPack=')
        filename = '/specsaversw-searchwords.csv'
        with open(here + filename) as f:
            reader = csv.reader(f)
            for row in reader:
                search_term = row[0].replace(' ', '+')
                yield Request(search_url % search_term, meta={'brand': row[1], 'dont_merge_cookies': True})

    def parse(self, response):
        products = response.xpath('//table[@id="res"]//tr[not(@id)]')
        for p in products:
            loader = ProductLoader(item=Product(), selector=p)
            name = p.xpath('td[@class="beskrivning"]/span/strong/text()').extract()[0].strip()
            quantity = p.xpath('td[@class="antal"]/text()').extract()
            if quantity:
                name = name + ' ' + quantity[0].strip()
            price = p.xpath('td[@class="pris"]/label[@class="GreyPrice"]/text()').extract()[0].strip()
            image_url = p.xpath('td[@class="beskrivning"]/a/img/@src').extract()[0].strip()
            product_id = p.xpath('td[@class="aterforsaljare"]/a/@href').re('\d+')[0]
            brand = response.meta['brand']
            categories = 'Kontaktlinser'
            dealer = p.xpath('td[@class="aterforsaljare"]/a/img/@title').extract()[0]
            in_stock = p.xpath('td[@class="levtid"]/label[contains(text(), "I lager")]')
            url = 'http://www.alltomlinser.se/LoadUrl.asp?id=' + product_id

            identifier = name + '-' + dealer

            loader.add_value('url', url)
            loader.add_value('price', price)
            loader.add_value('brand', brand)
            loader.add_value('category', categories)
            loader.add_value('url', url)
            loader.add_value('name', name)
            loader.add_value('image_url', image_url)
            loader.add_value('identifier', identifier)
            loader.add_value('sku', '')
            loader.add_value('dealer', dealer)
            if not in_stock:
                loader.add_value('stock', 0)
            yield loader.load_item()

        pages = response.xpath('//div[@id="PagDivPages"]//a/@href').extract()
        for page in pages:
            yield Request(response.urljoin(page), meta=response.meta)
