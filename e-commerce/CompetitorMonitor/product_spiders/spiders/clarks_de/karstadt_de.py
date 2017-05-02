# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.contrib.loader import ItemLoader
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy.http import Request, FormRequest
import re, time

from selenium import webdriver
from product_spiders.phantomjs import PhantomJS
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals


class KarstadtDeSpider(BaseSpider):

    name            = "karstadt_de"
    start_urls      = ["http://www.karstadt.de/schuhe/1421938458404/?prefn1=brand&prefv1=Ecco"]

    download_delay  = 2


    def __init__(self, *args, **kwargs):
        super(KarstadtDeSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_closed, signals.spider_closed)

        self._browser = PhantomJS.create_browser()

    def spider_closed(self):
        self._browser.close()



    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        total_items = hxs.select('//div[@class="results-hits"]/text()').re('von (\d+)')
        url = ''
        if total_items:
            url = response.url + '#prefn1=brand&sz='+total_items[-1]+'&prefv1=Ecco'
        else:
            url = response.url

        self._browser.get(url)
        hxs   = HtmlXPathSelector(text=self._browser.page_source)
        items = hxs.select("//ul[@id='search-result-items']/li")

        for item in items:

            l = {}

            l['name']       = item.select(".//h3[@class='product-name']/a/text()").extract()[0]
            l['url']        = item.select(".//div[@class='product-image']/a/@href").extract()[0]
            l['brand']      = item.select(".//h3[@class='product-name']/a/span/text()").extract()[0]
            l['image_url']  = item.select(".//div[@class='product-image']//img/@src").extract()[0]
            l['stock']      = 0

            yield Request(url=l['url'], meta={'l': l}, callback=self.parse_item, dont_filter=True)
        

    def parse_item(self, response):

        hxs  = HtmlXPathSelector(response)
        item = response.meta['l']

        data = hxs.select("//script[contains(text(),'prodid')]/text()").extract()[0]

        item['sku']        = re.findall(re.compile('prodid: \'(\d*)\''), data)[0]
        item['category']   = re.findall(re.compile('pcat: \'(.*)\''), data)[0].split(' - ')
        item['identifier'] = item['sku']
        item['price']      = re.findall(re.compile('value: \'(.*)\''), data)[0]

        if  item['price']:
            item['price']  = float(item['price'].replace(',', '.'))
            item['stock']  = 1


        l = ProductLoader(item=Product(), response=response)

        l.add_value('name',          item['name'])
        l.add_value('image_url',     item['image_url'])
        l.add_value('url',           item['url'])
        l.add_value('price',         item['price'])
        l.add_value('stock',         item['stock'])
        l.add_value('brand',         item['brand'])
        l.add_value('identifier',    item['identifier'])
        l.add_value('sku',           item['sku'])
        l.add_value('category',      item['category'])

        yield l.load_item()
