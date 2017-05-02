# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy.http import Request, FormRequest
import re, json, logging



class RobinsonsequestrianSpider(BaseSpider):

    name              = "robinsonsequestrian"
    allowed_domains   = ["robinsonsequestrian.com"]
    start_urls        = ["http://www.robinsonsequestrian.com"]
    base_url          = "http://www.robinsonsequestrian.com"


    def parse(self, response):

        hxs = HtmlXPathSelector(response)
        categories = hxs.select("//ul[@id='nav']/li[position()<8]//div[@class='level-0 dropdown']/ul/li/ul/li/a/@href").extract()
        categories.extend(hxs.select("//ul[@id='nav']/li[contains(@class,'clearance')]//div[@class='level-0 dropdown']/ul/li/ul/li/a/@href").extract())

        for category in categories:
            yield Request(url=category, callback=self.parse_category)


    def parse_category(self, response):

        hxs = HtmlXPathSelector(response=response)
        products = hxs.select("//ul[contains(@class,'products-grid')]/li")
        categories_tmp = hxs.select("//div[@class='breadcrumbs']//a")[1:]
        categories_tmp = [category.select("./span/text()").extract()[0] for category in categories_tmp]
        category_current = ''.join(hxs.select("//strong[@itemprop='title']/text()").extract()).strip()
        if category_current:
            categories_tmp.append(category_current)

        for product in products:

            name  = product.select(".//div[@class='product-name']/a/text()").extract()[0].strip()
            url   = product.select(".//div[@class='product-name']/a/@href").extract()[0]
            name  = " ".join(name.split())

            yield Request(url=url, meta={'name': name, 'categories_tmp': categories_tmp}, callback=self.parse_item)
        
        #== Look for the 'next page' button ==#
        try:
            next_page = hxs.select("//a[@title='Next']/@href").extract()[0]
            yield Request(next_page, callback=self.parse_category)
        except:
            pass
        

        
    def parse_item(self, response):

        hxs  = HtmlXPathSelector(response)

        name = response.meta['name']
        url  = response.url

        sku        = hxs.select("//p[@itemprop='identifier']/@content").extract()[0].replace('sku:', '').strip()
        brand      = ''.join(hxs.select("//span[@itemprop='brand']/text()").extract())
        image_url  = ''.join(hxs.select("//div[@class='product-img-box']//img[@id='image']/@src").extract())
        categories = hxs.select("//div[@class='breadcrumbs']//a")[1:]
        categories = [category.select("./span/text()").extract()[0] for category in categories]

        try:
            stock  = 1 if hxs.select("span[@itemprop='availability']/text()").extract()[0].strip() == 'In stock' else 0
        except:
            stock  = 0 if 'out of stock' in response.body.lower() else 1

        if not categories:
            categories = response.meta['categories_tmp']

        try:
            options = json.loads(re.findall(re.compile('\"productConfig\":(.+?),"productAttributes'), response.body)[0])
            options_names = json.loads('{' + re.findall(re.compile('{\"attributes\":.*(\"options.+?}]})'), response.body)[0])['options']
            options_names = dict((k, options_name['label']) for options_name in options_names for k in options_name['products'])
        except Exception as e:
            logging.error('No options found')
            options = None

        if options:
            for option in options:

                l = ProductLoader(item=Product(), response=response)

                option_id    = option
                saving_price = re.findall(re.compile('>(.+?)<'), options[option]['saving_price'])[0].encode('ascii', 'ignore')
                retail_price = re.findall(re.compile('>(.+?)<'), options[option]['retail_price'])[0].encode('ascii', 'ignore')
                option_price = round(float(retail_price) - float(saving_price), 2)
                sku_tmp      = sku + '-' + str(option_id)
                option_name  = options_names.get(option_id)

                try:
                    options[option]['stockAlertUrl']
                    stock  = 0
                except:
                    stock  = 1

                l.add_value('image_url',     image_url)
                l.add_value('url',           url)
                l.add_value('price',         option_price)
                l.add_value('stock',         stock)
                l.add_value('brand',         brand)
                l.add_value('identifier',    sku_tmp)
                l.add_value('sku',           sku_tmp)
                l.add_value('name',          name + ' ' + option_name)

                for category in categories:
                    l.add_value('category', category)

                yield l.load_item()

        else:

            l = ProductLoader(item=Product(), response=response)

            price = hxs.select("//span[@class='regular-price']/span[@class='price']/text()").extract()[0].strip()[1:].replace('[', '').replace(']', '')

            l.add_value('image_url',     image_url)
            l.add_value('url',           url)
            l.add_value('price',         price)
            l.add_value('stock',         stock)
            l.add_value('brand',         brand)
            l.add_value('identifier',    sku)
            l.add_value('sku',           sku)
            l.add_value('name',          name)

            for category in categories:
                l.add_value('category', category)

            yield l.load_item()