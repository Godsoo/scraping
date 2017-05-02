import re
import json
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest, HtmlResponse
from scrapy.utils.url import urljoin_rfc
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from scrapy import log


class Bondara(BaseSpider):
    name = 'bondara.co.uk'
    allowed_domains = ['bondara.co.uk', 'www.bondara.co.uk']
    start_urls = ('http://www.bondara.co.uk',)

    def __init__(self, *args, **kwargs):
        super(Bondara, self).__init__(*args, **kwargs)
        self.URL_BASE = 'http://www.bondara.co.uk'
        self.cookies = {}

    def start_requests(self):
        url = 'http://www.bondara.co.uk/cookies?fromPage=index'
        formdata = {'cookie_level': '4'}
        yield FormRequest(url=url, formdata=formdata)

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)
        # categories
        categories = hxs.select('//ul[contains(@class, "nav")]//a/@href').extract()
        for url in categories:
            url = urljoin_rfc(self.URL_BASE, url)
            yield Request(url, callback=self.parse_products_list)  # Request(url, cookies=self.cookies, callback=self.parse_products_list)

    def parse_products_list(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)
        items = hxs.select('//div[contains(@class, "itemBuy")]')
        for item in items:
            product_url = item.select('.//div[@class="itemName"]/a/@href').extract()[0]
            product_url = urljoin_rfc(self.URL_BASE, product_url)
            product_id = item.select('.//span[contains(@id,"price")]/@id').extract()
            price = item.select('.//span[contains(@id,"price")]/text()').extract()
            yield Request(product_url,
                          meta={'product_id': product_id,
                                'price': price},
                          callback=self.parse_product)  # Request(product_url, cookies=self.cookies, callback=self.parse_product)
        # next page
        next_page = hxs.select('//li[@class="next"]/a/@href').extract()
        if next_page:
            next_page = urljoin_rfc(self.URL_BASE, next_page[0])
            yield Request(next_page, callback=self.parse_products_list)  # Request(next_page, cookies=self.cookies, callback=self.parse_products_list)

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), response=response)
        name = hxs.select('//h1[@class="productTitle"]/span/text()').extract()
        if not name:
            self.log("ERROR name not found")
        else:
            name = " ".join(name[0].split())
            loader.add_value('name', name)
        loader.add_value('url', response.url)
        price = hxs.select('//span[contains(@id,"price")]/text()').re('\xa3(.*)')
        if not price:
            price = response.meta.get('price')
        if not price:
            self.log("WARNING: price not found")
            loader.add_value('price', '0.00')
        else:
            loader.add_value('price', price)
        sku = hxs.select('//span[@class="prdCode"]/text()').extract()
        if not sku:
            self.log("ERROR SKU not found")
        else:
            sku = sku[0].split()
            if len(sku) < 3:
                self.log("ERROR - wrong SKU format, needs checking")
            else:
                sku = sku[2]
                loader.add_value('sku', sku)
        # below xpath not working for products that are out of stock
        # product_id = hxs.select('//div[@class="addtomain"]//form/input[@name="shopAddItemId"]/@value').extract()
        product_id = hxs.select('//span[contains(@id,"price")]/@id').extract()
        if not product_id:
            product_id = response.meta.get('product_id')
        if not product_id:
            self.log("ERROR product ID not found")
            return
        else:
            product_id = product_id[0].split('_')
            if len(product_id) < 2:
                self.log("ERROR product ID not found")
            else:
                loader.add_value('identifier', product_id[1])
        product_image = hxs.select('//img[@name="mainimage"]/@src').extract()
        if not product_image:
            self.log("ERROR image not found")
        else:
            product_image = urljoin_rfc(self.URL_BASE, product_image[0].strip())
            loader.add_value('image_url', product_image)
        category = hxs.select('//ul[@id="breadcrumbs"]//a/text()').extract()
        if not category:
            self.log('ERROR no category found')
        else:
            loader.add_value('category', category[-1])

        if not hxs.select('//ul[@class="prodStock"]').extract():
            loader.add_value('stock', 0)

        options = hxs.select('//div[contains(@class, "itemsSelect")]//select[@class="selItem"]')
        if options and category and 'Sex Aids' in category:
            log.msg('CRAWL PRODUCT OPTIONS')
            option_values = ''.join(hxs.extract().split('vinfo = ')[-1].split(';\r\n')[0].split())
            option_values = option_values.replace(":'", "':").replace(',', ",'").replace('{', "{'").replace("':", "':'").replace(':[', "':[").replace(",'{", ',{')
            option_values = json.loads(option_values.replace("'", '"'))
            for option in option_values:
                product = loader.load_item()
                product['identifier'] = product['identifier'] + '-' + option['variety'][0]['vname']
                product['name'] = product['name'] + ' ' + option['variety'][0]['vname']
                product['price'] = option['price']
                option_loader = ProductLoader(item=product, response=response)
                yield option_loader.load_item()
        else:
            product = loader.load_item()
            yield product
