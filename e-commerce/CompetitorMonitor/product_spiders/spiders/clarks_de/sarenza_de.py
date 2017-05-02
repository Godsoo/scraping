# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.contrib.loader import ItemLoader
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy.http import Request, FormRequest
import re, time



class SarenzaDeSpider(BaseSpider):

    name = "sarenza_de"
    start_urls = ["http://www.sarenza.de/clarks",
                        "http://www.sarenza.de/ecco",
                        "http://www.sarenza.de/dune"]

    base_url = "http://www.sarenza.de/"



    def parse(self, response):

        hxs = HtmlXPathSelector(response)
        links = hxs.select("//section[@class='container ctr']/a/@href").extract()

        for link in links:
            link = self.base_url + link
            yield Request(url=link, callback=self.parse_category)


    def parse_category(self, response):

        hxs = HtmlXPathSelector(response)
        items = hxs.select("//div[@class='product-list-result']//ul[@class='vignettes']/li")

        for item in items:

            l = {}

            l['name'] = item.select(".//span[@class='model']/span/text()").extract()[0].strip()
            l['url'] = item.select("./a/@href").extract()[0]
            l['brand'] = item.select(".//strong[@class='brand']/span/text()").extract()[0].strip()
            l['image_url'] = item.select(".//div[@class='img-content']//img/@src").extract()[0]

            try:
                l['price'] = item.select(".//strong[@class='price slashed']/text()").extract()[1].strip()
            except:
                l['price'] = item.select(".//strong[@class='price']/i/text()").extract()[0].strip()

            l['stock'] = 0
            l['shipping'] = 0

            if  l['price']:
                l['price'] = re.findall(re.compile('(\d+.\d*.\d*)'), l['price'])[0].replace(',', '.')
                l['stock'] = 1

            yield Request(url=l['url'], meta={'l': l}, callback=self.parse_item, dont_filter=True)



        try:
            next_page = hxs.select("//footer[@class='pagination']//a[@title='Next']/@data-url").extract()[0]
            if not next_page == '#':
                next_page = "http://www.sarenza.de/homefh.aspx" + next_page
                yield Request(url=next_page, callback=self.parse_category, dont_filter=True)
        except:
            pass



    def parse_item(self, response):

        hxs = HtmlXPathSelector(response)
        item = response.meta['l']

        cat_01 = hxs.select("//ul[@class='breadcrumb']/li[3]//a/text()").extract()[0].strip()
        cat_02 = hxs.select("//ul[@class='breadcrumb']/li[4]//a/text()").extract()[0].strip()

        item['category'] = [cat_01, cat_02]
        item['sku'] = ''.join(hxs.select("//strong[text()='Artikelnummer']/parent::li/text()").extract()).strip()
        item['identifier'] = item['sku']


        l = ProductLoader(item=Product(), response=response)

        l.add_value('name', item['name'])
        l.add_value('image_url', item['image_url'])
        l.add_value('url', item['url'])
        l.add_value('price', item['price'])
        l.add_value('stock', item['stock'])
        l.add_value('brand', item['brand'])
        l.add_value('identifier', item['identifier'])
        l.add_value('sku', item['sku'])
        l.add_value('shipping_cost', item['shipping'])

        for category in item['category']:
            l.add_value('category', category)


        yield l.load_item()
