# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy.http import Request
import re
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
import json
from sonaeitems import SonaeMeta


class CurrysSpider(BaseSpider):
    name = "sonae-currys.co.uk"
    allowed_domains = ["currys.co.uk"]
    start_urls = ['http://www.currys.co.uk/gbuk/index.html']

    def parse(self, response):
        hxs = HtmlXPathSelector(response=response)
        base_url = get_base_url(response)
        for url in hxs.select('//*[@id="nav"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_categories)
        for url in hxs.select('//*[@id="nav"]//a/@data-rel').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_links)

    def parse_links(self, response):
        base_url = get_base_url(response)
        data = json.loads(response.body)
        hxs = HtmlXPathSelector(text=data['content'])
        for url in hxs.select('//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_categories)

    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response=response)
        base_url = get_base_url(response)
        links = hxs.select("//nav[@class = 'section_nav nested ucmsNav']/ul/li/a/@href").extract()
        categories = hxs.select("//nav/ul/li/div/a[@class = 'btn btnBold']/@href").extract()
        for category in categories:
            yield Request(urljoin_rfc(base_url, category), callback=self.parse_categories)
        for link in links:
            yield Request(urljoin_rfc(base_url, link), callback=self.parse_categories)

        items = hxs.select("//div[@class = 'col12 resultList']/article/a/@href").extract()
        try:
            new_page = hxs.select("//a[@class = 'next']/@href").extract()[0]
            yield Request(urljoin_rfc(base_url, new_page), callback=self.parse_categories)
        except:
            pass
        for item in items:
            yield Request(urljoin_rfc(base_url, item), callback=self.parse_items)

    def parse_items(self, response):
        hxs = HtmlXPathSelector(response=response)
        description_field = hxs.select("//script[@src = 'http://media.flixfacts.com/js/loader.js']").extract()[0]
        name = hxs.select("//span[@itemprop = 'name']/text()").extract()[0].encode('ascii', 'ignore')
        price = hxs.select("//meta[@property = 'og:price:amount']/@content").extract()[0]
        identifier = re.findall(re.compile('data-flix-mpn="(.+?)"'), description_field)[0]
        try:
            sku = re.findall(re.compile('data-flix-ean="(\d*)"'), description_field)[0]
        except:
            sku = ""
        categories = hxs.select("//div[@class = 'breadcrumb']/a/span/text()").extract()[1:4]
        brand = hxs.select("//span[@itemprop = 'brand']/text()").extract()[0]
        stock = hxs.select("//section[@class = 'col3']").extract()[0]
        stock = 1 if not re.findall(re.compile('Out of stock'), stock) else 0
        try:
            image_url = hxs.select("//div[@id = 'currentView']//img[@itemprop = 'image']/@src").extract()[0]
        except:
            image_url = ""
        l = ProductLoader(item=Product(), response=response)
        l.add_value('image_url', image_url)
        l.add_value('url', response.url)
        l.add_value('name', name)
        l.add_value('price', price)
        l.add_value('stock', stock)

        for category in categories:
            l.add_value('category', categories)

        l.add_value('brand', brand)
        l.add_value('sku', sku)
        l.add_value('identifier', identifier)
        product = l.load_item()

        product['metadata'] = SonaeMeta()
        if hxs.select('//span[@class="unavailable" and contains(text()[2], "Collect in store")]'):
            product['metadata']['exclusive_online'] = 'Yes'

        yield product
