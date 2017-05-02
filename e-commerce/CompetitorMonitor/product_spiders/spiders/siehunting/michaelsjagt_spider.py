import os
import re
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.fuzzywuzzy import process
from product_spiders.fuzzywuzzy import fuzz

HERE = os.path.abspath(os.path.dirname(__file__))

class MichaelsjagtSpider(BaseSpider):
    name = 'michaelsjagt.dk'
    allowed_domains = ['michaelsjagt.dk']
    start_urls = ['http://michaelsjagt.dk']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        categories =  hxs.select('//*[@id="nav"]/li/ul/li/a/@href').extract()
        for category in categories:
            url =  urljoin_rfc(get_base_url(response), category)
            yield Request(url+'?limit=all', callback=self.parse_categories)

    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//li[@class="item" or @class="item first" or @class="item last"]')
        if products:
            for product in products:
                url = product.select('h2/a/@href').extract()[0]
                yield Request(url, callback=self.parse_products)
        sub_cats = hxs.select('//ul[@class="left-nav"]/li//ul/li/a/@href').extract()
        for sub_cat in sub_cats:
            yield Request(sub_cat+'?limit=all', callback=self.parse_categories)

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        name =  hxs.select('//div[@class="product-name"]/h1/text()').extract()[0]
        price = float(re.sub("[^0-9].[^0-9]", "", ''.join(hxs.select('//div[@class="final-price"]/span[@class="price"]/text()').extract()).replace('.','').replace(',','.')))
        options = hxs.select('//div[@class="product-options"]/dl/dd/select/option[@value!=""]/text()').extract()
        options = [dict(zip(['desc','price'], option.split('+'))) for option in options]
        if options:
            for option in options:
                loader = ProductLoader(item=Product(), response=response)
                if 'price' in option:
                    option_price = float(re.sub("[^0-9].[^0-9]", "",option['price'].replace('.','').replace(',','.')))
                    loader.add_value('price', price + option_price)
                    if 'desc' in option:
                        loader.add_value('name', ' '.join((name,option['desc'])))
                    else:
                        loader.add_value('name', name)
                    loader.add_value('url', response.url)
                    yield loader.load_item()
                else:
                    loader.add_value('name', name)
                    loader.add_value('url', response.url)
                    loader.add_value('price', price)
                    yield loader.load_item()
        else:
            radio_options = hxs.select('//ul[@class="options-list"]/li') 
            if radio_options:
                for option in radio_options:
                    loader = ProductLoader(item=Product(), response=response)
                    desc = ''.join(option.select('span/label/text()').extract())
                    loader.add_value('name', ' '.join((name,desc)))
                    loader.add_value('url', response.url)
                    option_price = ''.join(option.select('span/label/span/span[@class="price"]/text()').extract()).replace('.','').replace(',','.')
                    if option_price:
                        loader.add_value('price', price + float(re.sub("[^0-9].[^0-9]", "", option_price)))
                    else:
                        loader.add_value('price', price)
                    yield loader.load_item()
            else:
                loader = ProductLoader(item=Product(), response=response)
                loader.add_value('name', name)
                loader.add_value('url', response.url)
                loader.add_value('price', price)
                yield loader.load_item()
