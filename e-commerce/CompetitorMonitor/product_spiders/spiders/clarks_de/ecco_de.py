# -*- coding: utf-8 -*-
import sys
sys.dont_write_bytecode = True

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


class EccoDeSpider(BaseSpider):

    name             = "ecco_de"
    start_urls       = ["http://shopeu.ecco.com/de/de/damen/alle-schuhe?page=1",
                        "http://shopeu.ecco.com/de/de/herren/alle-schuhe?page=1",
                        "http://shopeu.ecco.com/de/de/kinder?page=1",
                        "http://shopeu.ecco.com/de/de/sport/accessoires/alle-accessoires?page=1",
                        "http://shopeu.ecco.com/de/de/taschen/alle-sehen?page=1",
                        "http://shopeu.ecco.com/de/de/angeboten"]

    base_url         = "http://shopeu.ecco.com"
    download_delay   = 2


    def __init__(self, *args, **kwargs):
        super(EccoDeSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_closed, signals.spider_closed)

        self._browser = PhantomJS.create_browser()

    def spider_closed(self):
        self._browser.close()



    def parse(self, response):

        self._browser.get(response.url)
        time.sleep(2)
        hxs   = HtmlXPathSelector(text=self._browser.page_source)
        items = hxs.select("//ul[@id='product-list-cont']//a[@class='item-link']")

        for item in items:

            l = {}
            
            l['name']   = item.select(".//h3[@class='item-name']/text()").extract()[0]
            l['url']    = self.base_url + item.select("./@href").extract()[0]
            l['stock']  = 0
            l['brand']  = 'Ecco'

            yield Request(url=l['url'], meta={'l': l}, callback=self.parse_item)


        # There is a bug, sometimes pagination links not showing up so we have to manually go to the next page
        if items:
            current_page = re.findall(re.compile('page=(\d*)'), response.url)[0]
            next_page    = str(int(current_page) + 1)
            next_page    = response.url.replace('page='+current_page, 'page='+next_page)
            yield Request(url=next_page, callback=self.parse)
        
    

    def parse_item(self, response):

        hxs  = HtmlXPathSelector(response)
        item = response.meta['l']

        item['category'] = hxs.select("//div[@itemprop='breadcrumb']/a[@class='cat']/text()").extract()[0].strip()
        item['category'] = 'Accessories' if item['category'].lower() == 'taschen' else item['category']

        options = hxs.select("//div[@class='bx-color']/ul/li")
        option_main_part = hxs.select("//meta[@itemprop='productID']/@content").extract()[0].split('-')[0].replace('sku:', '').strip()
        constant_name = item['name']

        for option in options:

            option_postfix    = option.select("./@opt-style_key").extract()[0].split('_')[-1]
            option_name       = option.select("./@title").extract()[0]
            item['name']      = constant_name + ' ' + option_name
            item['image_url'] = hxs.select(".//img/@src").extract()[0]
            try:
                item['price'] = hxs.select("//div[@class='bx-nameprice clr']/div[contains(@class,{})]/div/text()".format(option_postfix)).extract()[0].strip()
            except:
                continue
            if  item['price']:
                item['price'] = re.findall(re.compile('(\d+.\d*.\d*)'), item['price'])[0]
                item['stock'] = 1
                item['shipping'] = '2.95' if float(item['price']) < 49 else 0 

            item['sku'] = option_main_part + '-' + option_postfix
            item['identifier'] = item['sku']


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
            l.add_value('shipping_cost', item['shipping'])

            yield l.load_item()
