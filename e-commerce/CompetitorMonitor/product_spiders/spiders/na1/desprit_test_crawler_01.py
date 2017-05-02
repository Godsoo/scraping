# -*- coding: utf-8 -*-
from scrapy.contrib.spiders import CrawlSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.contrib.loader import ItemLoader
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

import re

class CakeSpider(CrawlSpider):
    name = "cakedecorating"
    allowed_domains = ["thecakedecoratingcompany.co.uk"]
    start_urls = ["http://www.thecakedecoratingcompany.co.uk/catalog/"]

    def parse(self, response):
        '''Parse home page and extract all categories from side menu'''

        hxs = HtmlXPathSelector(response)
        # There are two blocks with categories on website with slightly different class name
        categories_01 = hxs.select("//div[@class='vertitem ']/a/@href").extract()
        categories_02 = hxs.select("//div[@class='vertitem']/a/@href").extract()
        categories_03 = []

        for i in categories_02:
            if 'http://' not in i:
                categories_03.append('http://www.thecakedecoratingcompany.co.uk/catalog/' + i)
            else:
                categories_03.append(i)

        categories = categories_01 + categories_03

        for category in categories:
            yield Request((category), callback=self.parse_category)

    def parse_category(self, response):
        '''Recursive function, it looks for items and categories on the page,if 
        it finds an item, it calls next function, but if it finds another category, 
        it just calls itself again till there is no more categories to be parsed'''

        hxs = HtmlXPathSelector(response)
        new_categories = hxs.select("//div[@class='box1']/a/@href").extract()
        items = hxs.select("//span[@class='tx2']/a/@href").extract()

        try:
            new_page = hxs.select("//a[@title=' Next Page ']/@href").extract()[0]
            if new_page:
                yield Request(new_page, callback=self.parse_category)
        except:
            pass

        for new_category in new_categories:
            link = 'http://www.thecakedecoratingcompany.co.uk/catalog/' + new_category
            yield Request(link, callback=self.parse_category)

        for item in items:
            yield Request(item, callback=self.parse_item)

    def parse_item(self, response):
        '''Parse page of particular product'''

        l = ProductLoader(item=Product(), response=response)
        hxs = HtmlXPathSelector(response)

        try:
            item_name = hxs.select("//span[@class='txcake']/text()").extract()[0]
            item_code = hxs.select("//span[@class='txcake']/span[@class='smallText']/text()").extract()[0]
        except:
            item_code = 0

        try:
            item_image = hxs.select("//div[@id='backdrop']/img").extract()[1]
            item_image = re.findall(re.compile('src=\"(.+?)\"'), item_image)[0]
            base_url = get_base_url(response)
            item_image = urljoin_rfc(base_url, item_image)
        except:
            item_image = ''

        # if there is no <span> with 'instock' class on the page, then the item is out of stock
        # if it is not out of stock, we exptract it's price too. There are three types of price:
        # 1) price with discount; 2) list of prices depending on quntity; 3) simple price case
        try:
            stock_status = hxs.select("//span[@class='instock']/b/text()").extract()[0]

            item_price = hxs.select("//span[@class='tx2']//td[@class='infoBoxContents']/span[@class='productSpecialPrice']/text()").extract()
            if item_price:
                item_price = item_price[0]
            else:
                item_price = hxs.select("//span[@class='tx2']//td[@class='infoBoxContents']/text()").extract()
                if item_price:
                    item_price = item_price[1]
                else:
                    item_price = hxs.select("//span[@class='tx2']/span[@class='productSpecialPrice']/text()").extract()
                    if item_price:
                        item_price = item_price[0]
                    else:
                        item_price = hxs.select("//span[@class='tx2']/text()").extract()
                        if item_price:
                            item_price = item_price[0]
                        else:
                            item_price = 0.00

            stock_status = 1
        except:
            stock_status = 0
            item_price = 0.00

        item_id = hxs.select("//input[@name='products_id']/@value").extract()[0]
        # extract from string as '[46P10009] Weight: 10 grams / 0.35 oz' the code in brackets
        product_code_pattern = re.compile('\[(.+?)\]')
        product_code = re.findall(product_code_pattern, item_code)[0] if item_code else 0

        # delete currency tag, white spaces and new line symbols
        string_clearing = ['\n', '\xa0', '\xa3']
        if item_price:
            for i in string_clearing:
                item_price = re.sub(i, '', item_price)

        if item_price:
            shipping_price = 2.50 if float(item_price) < 25.00 else 0.00
        else:
            shipping_price = 0.00

        l.add_value('price', float(item_price))
        l.add_value('stock', stock_status)
        l.add_value('shipping_cost', shipping_price)
        l.add_value('identifier', item_id)
        l.add_value('sku', 	     product_code)
        l.add_value('url', 	     response.url)
        l.add_value('name', 		 item_name)
        l.add_value('image_url', item_image)

        yield l.load_item()
