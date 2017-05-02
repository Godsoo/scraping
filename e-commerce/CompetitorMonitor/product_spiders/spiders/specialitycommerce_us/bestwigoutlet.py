# -*- coding: utf-8 -*-

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import HtmlResponse, Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin
import re
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

times = 0
HEADERS = {'X-Requested-With':'XMLHttpRequest', 'User-Agent':
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.81 Safari/537.36'}

class BestWigOutlet(BaseSpider):
    name = "bestwigoutlet.com"
    allowed_domains = ["bestwigoutlet.com"]
    start_urls = ["http://www.bestwigoutlet.com/"]


    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        category_urls = hxs.select('//*[@class="megamenu-bott-border"]/a/@href').extract()
        for idx, url in enumerate(category_urls):
            yield Request(urljoin(base_url, url), callback=self.parse_category, meta={'cookiejar':idx})

    def parse_category(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        product_urls = hxs.select('//table[@class="item"]//tr[1]//a/@href').extract()
        next_page_url = hxs.select('//a[contains(@title, "Next Page")]/@href').extract()
        for url in product_urls:
            yield Request(urljoin(base_url, url), callback=self.parse_product, meta=response.meta)
        if next_page_url:
            yield Request(next_page_url[0], callback=self.parse_category, meta=response.meta)

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        global times

        loader = ProductLoader(selector=hxs, item=Product())
        name = hxs.select('//h1[@id="div_product_name"]/text()').extract()

        loader.add_xpath('name', '//h1[@id="div_product_name"]/text()')
        try:
            name = name[0]
        except:
            times += 1
            self.log('Name error with %s repeates %s' %(response.url, times))
            if times < 10:
                yield Request(response.url, dont_filter=True, callback=self.parse_product)
#            self.log('Name error on %s. Got name %s. Response body is' %(response.url, name, response.body))
            return 
        brand = re.findall(r'by (.*)$', name)
        if brand:
            brand = brand[-1]
        loader.add_value('brand', brand)
        stock = 0
        price = hxs.select('//span[@id="div_product_price"]//text()').extract()
        if price:
            price = price[-1]
            stock = 1
        else:
            self.log('Price error on %s. Got price %s. Response body is %s' %(response.url, price, response.body))
        loader.add_value('price', price)
        loader.add_value('stock', stock)
        category = hxs.select('//a[@class="nav-location"]/text()').extract()
        del category[0]
        loader.add_value('category', category)
        sku = hxs.select('//span[@id="div_product_itemno"]/text()').extract()
        if sku:
            sku = sku[0]
        loader.add_xpath('sku', '//span[@id="div_product_itemno"]/text()')
        loader.add_xpath('identifier', '//span[@id="div_product_itemno"]/text()')
        loader.add_value('url', response.url)
        image_url = hxs.select('//img[@id="target_img"]/@src').extract()
        if image_url:
            image_url = image_url[0]
            loader.add_value('image_url', urljoin(base_url, image_url))
        product = loader.load_item()
        times = 0
        options = hxs.select('//img[@class="avail_colors"]')
        if not options:
            options = hxs.select('//select[@id="optionChoice"]/option[not(@value="")]/text()').extract()
            if not options:
                yield product
                return
            for option in options:
                product['identifier'] = '-'.join((sku, option))
                product['name'] = ' '.join((name, option))
                yield product
            return
        for option in options:
            product['identifier'] = option.select('./@id').extract()[0]
            image_url = option.select('./@src').extract()[0]
            product['image_url'] = urljoin(base_url, image_url)
            option_sku = option.select('./@sku').extract()
            if option_sku:
                option_sku = option_sku[0]
            else:
                option_sku = option.select('./@alt').extract()[0]
            option_name = re.findall(r'- +(.*)', option_sku)
            if option_name:
                product['name'] = ' '.join((name, option_name[0]))
            else:
                product['name'] = ' '.join((name, option_sku))
            yield product
