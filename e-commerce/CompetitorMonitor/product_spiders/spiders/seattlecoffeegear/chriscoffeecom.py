import logging
import re
from copy import copy

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoader

class ChriscoffeeComSpider(BaseSpider):
    name = 'chriscoffee.com'
    allowed_domains = ['chriscoffee.com', 'wysrt.cnwfk.servertrust.com']
    start_urls = ('http://www.chriscoffee.com/category_s/7240.htm', # Food
                  'http://www.chriscoffee.com/category_s/7520.htm', # Office
                  'http://www.chriscoffee.com/category_s/2164.htm', # Coffee
                  'http://www.chriscoffee.com/Home_Espresso_s/2645.htm', #Home
                  'https://www.chriscoffee.com/Grinders_s/2099.htm') #Grinders
                  #'http://www.chriscoffee.com/category_s/2781.htm')

    download_delay = 2

    def parse(self, response):
        URL_BASE = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        products =  hxs.select('//table/tr/td/table/tr/td/a/@href').extract()
        if products:
            yield Request(response.url, dont_filter=True, callback=self.parse_all_products)

        # sub_category urls
        sub_category_urls = hxs.select('//table/tr/td/div/span/span/a/@href').extract()
        for url in sub_category_urls:
            yield Request(url, callback=self.parse_subcategory)

    def parse_subcategory(self, response):
        URL_BASE = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        urls = hxs.select('//table/tr/td/div/span/span/a/@href').extract()
        if urls:
            for url in urls:
                url = urljoin_rfc(URL_BASE, url)
                yield Request(url, callback=self.parse_all_products)
        else: 
            products =  hxs.select('//table/tr/td/table/tr/td/a/@href').extract()
            if products:
                yield Request(response.url, dont_filter=True, callback=self.parse_all_products)

    def parse_all_products(self, response):
        hxs = HtmlXPathSelector(response)
        products =  hxs.select('//table/tr/td/table/tr/td/a/@href').extract()
        if products:
            cat = hxs.select('//input[@name="Cat"]/@value').extract()[0]
            total = re.findall("(\d+)", hxs.select('//div[@class="matching_results_text"]/text()').extract()[0])[0]
            url = response.url + '?searching=Y&sort=1&cat=%s&show=%s&page=1' % (cat, total)
            yield Request(url, dont_filter=True, callback=self.parse_products)
        else:
            yield Request(response.url, dont_filter=True, callback=self.parse_subcategory)

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        products =  hxs.select('//table/tr/td/table/tr/td/a/@href').extract()
        if not products:
            yield Request(response.url, dont_filter=True, callback=self.parse_subcategory)
        else:
            for product in products:
                yield Request(product, dont_filter=True, callback=self.parse_product)
 
    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        image_url = hxs.select('//meta[@property="og:image"]/@content').extract()
        if image_url:
            image_url = urljoin_rfc(base_url, image_url[0])

        category = hxs.select('//td[contains(@class,"breadcrumb")]//a/text()').extract()
        if category:
            category = category[-1].strip()

        brand = hxs.select('//div[contains(@id, "ProductDetail_Tech")]//table//tr/td[contains(text(),"Manufacturer")]/following-sibling::td/text()').extract()
        if brand:
            brand = brand[0].strip()

        out_of_stock = hxs.select('//td[contains(@id,"productdetail-action-wrapper")]//span[contains(text(),"Call for best price!")]/text()')

        sub_products = hxs.select('//tr[@class="Multi-Child_Background"]')
        if sub_products:
            for sub_product in sub_products:
                loader = ProductLoader(item=Product(), selector=sub_product)
                loader.add_xpath('name', 'td[@class="productnamecolorSMALL colors_productname"]/text()')
                loader.add_xpath('sku', 'td[@class="smalltext colors_text"]/text()')
                loader.add_xpath('identifier', 'td[@class="smalltext colors_text"]/text()')
                loader.add_value('url', response.url)
                loader.add_xpath('price', 'td[@class="smalltext colors_text"]/b/div/div/span/text()')
                loader.add_value('category', category)
                loader.add_value('image_url', image_url)
                loader.add_value('brand', brand)
                if out_of_stock:
                    loader.add_value('stock', 0)
                yield loader.load_item()
        else:
            if hxs.select('//table[@id="options_table"]//select'):
                select_options = []
                for select in hxs.select('//table[@id="options_table"]//select'):
                    select_options.append(select.select('option/text()').extract())
                name = hxs.select('//span[@itemprop="name"]/text()').extract()[0]
                full_names = select_options[0]
                for i, full_name in enumerate(full_names):
                    for options in select_options[1:]:
                        for option in options:
                            full_names[i] = full_names[i] + ' ' + option
                for full_name in full_names:
                    loader = ProductLoader(item=Product(), response=response)
                    loader.add_value('name', name + ' ' + full_name)
                    loader.add_xpath('sku', '//span[@class="product_code"]/text()')
                    loader.add_xpath('identifier', '//span[@class="product_code"]/text()')
                    loader.add_value('url', response.url)
                    price = hxs.select('//span[@itemprop="price"]/text()').extract()
                    price = price[0] if price else 0
                    loader.add_value('price', price)
                    loader.add_value('category', category)
                    loader.add_value('image_url', image_url)
                    loader.add_value('brand', brand)
                    if out_of_stock:
                        loader.add_value('stock', 0)
                    yield loader.load_item()
            else:
                loader = ProductLoader(item=Product(), response=response)
                loader.add_xpath('name', '//span[@itemprop="name"]/text()')
                loader.add_xpath('sku', '//span[@class="product_code"]/text()')
                loader.add_xpath('identifier', '//span[@class="product_code"]/text()')
                loader.add_value('url', response.url)
                loader.add_value('category', category)
                loader.add_value('image_url', image_url)
                loader.add_value('brand', brand)
                if out_of_stock:
                    loader.add_value('stock', 0)
                price = hxs.select('//span[@itemprop="price"]/text()').extract()
                price = price[0] if price else 0
                loader.add_value('price', price)
                yield loader.load_item()
