# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy.http import Request, FormRequest
import re, json, logging

from product_spiders.utils import extract_price_eu


class Light11Spider(BaseSpider):

    name              = "light11.de"
    start_urls        = ["http://www.light11.de/Luceplan/"]


    base_url          = "http://www.dmlights.be"
    download_delay    = 1


    def parse(self, response):

        hxs = HtmlXPathSelector(response)
        links = hxs.select("//ul[@id='productList']/li/a/@href").extract()
        for link in links:
            link = re.sub('\?force_sid=(.*)', '', link)
            yield Request(url=link, callback=self.parse_page)

        try:
            next_page = hxs.select("//div[contains(@class,'t_icon_nextpage')]/parent::a/@href").extract()[0]
            next_page = re.sub('\?force_sid=(.*)', '', next_page)
            yield Request(url=next_page, callback=self.parse)
        except:
            pass

    

    def parse_page(self, response):

        hxs = HtmlXPathSelector(response)

        categories  = hxs.select("//div[@id='breadCrumb']//a[@title='Luceplan']/following-sibling::a/@title").extract()
        name  = hxs.select("//h1[@id='productTitle']/span[@itemprop='name']/text()").extract()[0]
        brand = 'Luceplan'
        image_url  = hxs.select("//div[@id='productinfo']//a[contains(@id,'zoom')]/@href").extract()
        image_url  = 'http://' + image_url[0].replace('//', '') if image_url else None
        url = response.url

        options = hxs.select("//div[@id='productmainrightInfo']//button[@name='toBasket']")
        for option in options:
            option_name  = ''.join(option.select("./preceding::h3[contains(@class,'diInBlo')][1]/text()").extract())
            option_price = ''.join(option.select("./preceding::div[contains(@class,'variant_price')][1]/text()").extract())
            option_price = option_price.encode('ascii', 'ignore') if option_price else option_price
            option_price = option_price.split(',')[0] if option_price.split(',')[1] == '-' else option_price
            option_id    = ''.join(option.select("./@id").extract()).replace('toBasket_', '')

            sku = identifier = option_id

            stock = option.select("./preceding::div[contains(@class,'notOnStockYellow')]/text()").extract()
            if not stock:
                stock = option.select("./preceding::div[contains(@class,'OnStock')]/text()").extract()
            stock = 1 if stock else 0

            option_name    = name + " " + option_name

            l = ProductLoader(item=Product(), response=response)

            l.add_value('brand', brand)
            l.add_value('name', option_name)
            l.add_value('image_url', image_url)
            l.add_value('url', url)
            l.add_value('stock', stock)
            l.add_value('sku', sku)
            l.add_value('identifier', identifier)
            l.add_value('price', extract_price_eu(str(option_price)))
            if l.get_output_value('price')<= 99:
                l.add_value('shipping_cost', 5.50)

            for category in categories:
                l.add_value('category', category)

            yield l.load_item()
