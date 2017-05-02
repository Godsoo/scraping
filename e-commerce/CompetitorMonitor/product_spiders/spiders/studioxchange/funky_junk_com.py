from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin as urljoin_rfc
from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
import json
import re

from scrapy import log

class FunkyJunkComSpider(BaseSpider):
    name = 'www.funky-junk.com'
    allowed_domains = ['www.proaudioeurope.com']
    start_urls = ['http://www.proaudioeurope.com/']
    

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//div[@class="nav-container"]//a[not(contains(@href, "info"))]/@href').extract():
            yield Request(urljoin_rfc(base_url, url + '?limit=30'), callback=self.parse_category)

    def parse_category(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//*[@id="products-list"]/li//h2/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)
        for url in hxs.select('//div[@class="pager"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url + '?limit=30'), callback=self.parse_category)

    @staticmethod
    def parse_product(response):
        base_url = get_base_url(response)
        body = response.body.decode('utf-8', 'ignore')
        hxs = HtmlXPathSelector(text=body)

        price = hxs.select('//*[@id="inc-tax"]/span[@class="price"]/text()').extract()
        price2 = hxs.select('//*[@id="inc-tax"]/p[@class="uk-listprice"]/text()').extract()
        if not price:
            return
        product_price = extract_price(price[0])
        if not product_price and price2:
            product_price = extract_price(price2[0])

        product_id = hxs.select('//*[@id="product_addtocart_form"]//input[@name="product"]/@value').extract()
        product_identifier = product_id[0]
        brand = hxs.select('//div[@class="prod-brand-name"]/a/text()').extract()
        brand = brand[0] if brand else ''
        product_name = hxs.select('//div[@class="product-view"]/h1/text()').extract()[0]
        image_url = hxs.select('//p[@class="product-image"]/a/@href').extract()
        category = hxs.select('//div[@class="breadcrumbs"]/li[2]/a/text()').extract()

        stock = ''.join(hxs.select('//div[@class="prod-view-ship"]/p/text()').extract()).strip()
        #self.log("STOCKINFO: {}".format(stock))

        options = hxs.select('//select[@class=" required-entry product-custom-option"]/option')
        radio_options = hxs.select('//ul[@class="options-list"]//li')
        prices = {}
        if options or radio_options:
            options_config = re.search(r'var opConfig = new Product\.Options\((.*?)\);', response.body)
            product_data = json.loads(options_config.groups()[0])
            for data in product_data.itervalues():
                for option_id, p in data.iteritems():
                    prices[option_id] = p['price']
        if options and radio_options:
            labels = hxs.select('//div[@class="product-options"]//dt/label/text()').extract()
            for radio_option in radio_options:
                radio_identifier = radio_option.select('./input/@value').extract()[0]
                radio_name = radio_option.select('.//label/text()').extract()[0]
                radio_prices = radio_option.select('.//span[@class="price"]/text()').extract()
                if radio_prices:
                    radio_price = max(map(extract_price, radio_prices))
                else:
                    radio_price = 0
                for option in options:
                    option_identifier = option.select('./@value').extract()
                    if not option_identifier or option_identifier[0] == '':
                        continue
                    name = "{}, {}: {}, {}: {}".format(product_name,
                                                       labels[0],
                                                       radio_name,
                                                       labels[1],
                                                       option.select('./text()').extract()[0].encode('utf-8'))
                    identifier = "{}-{}-{}".format(product_identifier,
                                                   radio_identifier,
                                                   option_identifier[0])
                    loader = ProductLoader(response=response, item=Product())
                    loader.add_value('identifier', identifier)
                    # INC VAT: Select max price
                    prices = option.select('text()').re('\((.*?)\)')
                    if prices:
                        price = radio_price + max(map(extract_price, prices))
                    else:
                        price = radio_price

                    #price = prices[option_identifier[0]]

                    if price<=0:
                        price = product_price
                    loader.add_value('price', price)
                    loader.add_value('brand', brand)
                    loader.add_value('url', response.url)
                    loader.add_value('name', name.decode('utf-8'))
                    if image_url:
                        loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
                    if category:
                        loader.add_value('category', category[0])
                    if stock == 'Out of stock':
                        loader.add_value('stock', 0)
                    yield loader.load_item()

        elif options or radio_options:
            options = options if options else radio_options
            for option in options:
                if radio_options:
                    identifier = option.select('./input/@value').extract()[0]
                    if identifier == '':
                        identifier = product_identifier
                    name = product_name + ", " + option.select('.//label/text()').extract()[0]
                    prices = option.select('.//span[@class="price"]/text()').extract()
                    if prices:
                        price = max(map(extract_price, prices))
                    else:
                        price = 0
                else:
                    identifier = option.select('./@value').extract()
                    if not identifier or identifier[0] == '':
                        continue
                    else:
                        identifier = identifier[0]
                    option_name = option.select('./text()').extract()[0]
                    option_name = option_name.split(u'\xa3')[0].strip()
                    name = product_name + ", " + option_name
                    prices = option.select('text()').re('\((.*?)\)')
                    if prices:
                        price = max(map(extract_price, prices))
                    else:
                        price = price

                identifier = product_identifier + "-" + identifier
                loader = ProductLoader(response=response, item=Product())
                loader.add_value('identifier', identifier)
                if price<=0:
                    price = product_price
                loader.add_value('price', price)
                loader.add_value('brand', brand)
                loader.add_value('url', response.url)
                loader.add_value('name', name)
                if image_url:
                    loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
                if category:
                    loader.add_value('category', category[0])
                if stock == 'Out of stock':
                    loader.add_value('stock', 0)
                yield loader.load_item()
        else:
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('identifier', product_identifier)
            loader.add_value('price', product_price)
            loader.add_value('brand', brand)
            loader.add_value('url', response.url)
            loader.add_value('name', product_name)
            if image_url:
                loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            if category:
                loader.add_value('category', category[0])
            if stock == 'Out of stock':
                loader.add_value('stock', 0)
            yield loader.load_item()
