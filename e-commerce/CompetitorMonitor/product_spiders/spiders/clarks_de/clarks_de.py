# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.contrib.loader import ItemLoader
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy.http import Request, FormRequest
import re, time



class ClarksDeSpider(BaseSpider):

    name             = "clarks_de"
    start_urls       = ["http://www.clarks.de/c/damenschuhkollektion",
                        "http://www.clarks.de/c/herrenschuhkollektion"]

    base_url         = "http://www.clarks.de"


    def parse(self, response):

        hxs = HtmlXPathSelector(response = response)
        yield Request(url=response.url, callback=self.parse_page, dont_filter=True)

        try:
            next_page = hxs.select("//link[@rel='next']/@href").extract()[0]
            yield Request(url=next_page, callback=self.parse)
        except:
            pass


    def parse_page(self, response):

        hxs   = HtmlXPathSelector(response = response)
        items = hxs.select("//li[@class='product-list-item ']")

        for item in items:

            l = {}

            l['sku']        = item.select("./span[@class='product-name-header']/a/@data-productid").extract()[0]
            name_1          = item.select("./span[@class='product-name-header']/a/@data-prodname").extract()[0]
            
            try:
                name_2      = item.select(".//span[@class='product-colour-header']/text()").extract()[0]
            except:
                name_2      = ''

            try:
                name_3      = item.select(".//span[@class='product-category-header']/text()").extract()[0]
            except:
                name_3      = ''

            l['name']       = u'{} {} {}'.format(name_1, name_2, name_3).replace('  ', ' ')
            l['category']   = item.select("./span[@class='product-name-header']/a/@data-prodcategory").extract()[0]
            l['category']   = 'Accessories' if 'bags' in response.url else l['category']
            l['url']        = self.base_url + item.select("./span[@class='product-name-header']/a/@href").extract()[0]
            l['image_url']  = 'http://' + item.select(".//img[contains(@src,'assets')]/@src").extract()[0][2:]
            l['stock']      = 0
            l['brand']      = 'Clarks'

            yield Request(url=l['url'], meta={'l': l}, callback=self.parse_item)
    

    def parse_item(self, response):

        hxs = HtmlXPathSelector(response)
        l   = response.meta['l']

        l['price'] = re.findall(re.compile('product_price_string:\"(\d+.\d*.\d*)"'), response.body)[0]

        if  l['price']:
            l['price']  = re.findall(re.compile('(\d+.\d*.\d*)'), l['price'])[0]
            l['stock']  = 1

        l['identifier'] = l['sku']

        
        item = ProductLoader(item=Product(), response=response)

        item.add_value('name',          l['name'])
        item.add_value('image_url',     l['image_url'])
        item.add_value('url',           l['url'])
        item.add_value('price',         l['price'])
        item.add_value('stock',         l['stock'])
        item.add_value('brand',         l['brand'])
        item.add_value('identifier',    l['identifier'])
        item.add_value('sku',           l['sku'])
        item.add_value('category',      l['category'])


        yield item.load_item()
