from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector

from scrapy.http import Request

from scrapy.utils.response import get_base_url

#from scrapy.utils.url import  urljoin_rfc

from product_spiders.items import Product, ProductLoader

import logging
import re

class FaceTheFutureSpider(BaseSpider):
    name = "facethefuture-trial-facethefuture"
    allowed_domains = ["www.facethefuture.co.uk"]
    start_urls = (
        "http://www.facethefuture.co.uk/shop",
    )

    products_parsed = []

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        brands = hxs.select('//ul[@class="catTreeTop"]//li//a/@href').extract()
        categories = hxs.select('//ul[@id="mainmenu-nav"]/li/a/@href').extract()

        for brand in brands:
            #A brand page is either a product listing or a category page.
            #if this is a subcategory page, pass parsing
            subcats = hxs.select('//ul[@id="subCats"]').extract()
            logging.error("BRAND")
            logging.error(brand)
            logging.error("PRESENT")
            logging.error(subcats)
            if not subcats:
                yield Request(brand, callback=self.parse_listing)

        for cat in categories:
            pass
            #yield Request(cat, callback=self.parse_listing)


    def parse_listing(self, response):
        hxs = HtmlXPathSelector(response)
        links = hxs.select('//div[@class="product_list"]//div//h2/a/@href').extract()

        for link in links:
            yield Request(link, callback=self.parse_product)

        pages = hxs.select('//div[@class="pagination_2"]//a[@class="txtLink"]')
        if pages:
            for page in pages:
                if '>' in page.select('text()').extract():
                    link = page.select('@href').extract()[0]
                    yield Request(link, callback=self.parse_listing)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        if response.url in self.products_parsed:
            return
        loader = ProductLoader(response=response, item=Product() )
        logging.error("RESPONSE URL")
        logging.error(response.url)

        desc = hxs.select('//div[@id="product_description"]')

        #Determine if this is a normal price listing or action price
        special_price = hxs.select('//div[@class="item_price"]//span[@class="txtSale"]/text()').extract()

        if special_price:
            #there is a special price
            price = hxs.select('//div[@class="item_price"]//span[@class="txtSale"]/text()').extract()[0][1:]
        else:
            #There is a price in the text
            price_raw = desc.select('//p[2]/span[1]/text()').extract()
            if price_raw:
                price_less_raw = desc.select('//p[2]/span[1]/text()').extract()[0][2:]
                price = price_less_raw.split(" ")[0]
            else:
                #There is a price in the special box but its a normal price
                price_raw = hxs.select('//div[@class="item_price"]//span[@class="txtPrice"]/text()').extract()[0]
                if "Call" in price_raw:
                    price = "No price stated"
                else:
                    price = hxs.select('//div[@class="item_price"]//span[@class="txtPrice"]/text()').extract()[0][1:]

        oos = hxs.select('//span[@class="txtOutOfStock"]/text()').extract()

        #Same on normal and special offer page
        sku_raw = desc.select('text()[last()]').extract()[0]
        sku = sku_raw.rstrip().strip(' ')

        if not sku:
            #Produces list of 
            sku_raw = desc.select('text()').extract()
            pattern = r'[A-Z0-9]+'
            for el in sku_raw:
                match = re.search(pattern, el)
                if match:
                    sku = match.group()
                    continue

        identifier = hxs.select('//input[@name="add"]/@value').extract()[0]

        #Same on normal and special offer page
        img_url = hxs.select('//div[@id="product_img_col"]//img[last()]/@src').extract()[0]
        img_url = '%s%s' % ('http://www.facethefuture.co.uk', img_url)
        #Same on normal and special offer page
        category = hxs.select('//div[@id="product_description"]/a/text()').extract()

        #Same on normal and special offer page
        brand = hxs.select('//div[@class="location"]//a[@class="txtLocation"][1]/text()').extract()

        #Same on normal and special offer page
        name = hxs.select('//div[@id="middle_col_2"]//form//h1/text()').extract()

        self.products_parsed.append(response.url)

        logging.error("PRODUCT")
        logging.error(identifier)
        logging.error(name)
        logging.error(price)
        logging.error(category)
        logging.error(img_url)
        logging.error(brand)

        loader.add_value('name', name)
        loader.add_value('price', price)
        loader.add_value('url', response.url)
        loader.add_value('identifier', identifier)
        loader.add_value('sku', sku)
        if oos:
            loader.add_value('metadata', 'Out of stock')
        loader.add_value('image_url', img_url)
        if category:
            loader.add_value('category', category)
        if 'CLEARANCE' not in brand[0]:
            loader.add_value('brand', brand[0])
        else:
            loader.add_value('category', "Clearance products")
        loader.add_value('shipping_cost', 'N/A')

        yield loader.load_item()
