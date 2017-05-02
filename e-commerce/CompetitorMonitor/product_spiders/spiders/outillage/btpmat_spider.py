# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse

from product_spiders.utils import extract_price_eu as extract_price

from product_spiders.items import Product, ProductLoader
import re


class BtpMat_spider(BaseSpider):
    name = 'btpmat.fr'
    allowed_domains = ['btpmat.fr', 'www.btpmat.fr']
    start_urls = ('http://www.btpmat.fr',)

    def parse_products(self, response):

        hxs = HtmlXPathSelector(response)

        products = hxs.select('//li[contains(@class,"hreview-aggregate hproduct")]')
        for p in products:
            url = p.select('.//div/div/span/a/@href')[0].extract()
            name = p.select('.//div/div/span/a/text()')[0].extract()
            price = p.select('.//div/div/div/span/small/text()').re(r'([0-9\.\, ]+)')

            if not price:
                yield Request(url, callback=self.parse_product_options, meta={'name': name})
            else:
                price = price[0]
                yield Request(url, callback=self.parse_product, meta={'price': price, 'name': name})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        meta = response.meta

        sku = hxs.select('//p[@class="alignright"]/text()').extract()[0].replace('[', '').replace(']', '')
        category = hxs.select('//div[@class="breadcrumbs"]/ul/li/a/text()').extract()[-1]
        name = response.meta.get('name')

        price_box = hxs.select("//div[@itemprop='offers']//*[contains(text(),'HT')]/text()").extract()
        if price_box:	
            price_box = ''.join(price_box[0].split())
            price = re.findall(re.compile("[^0-9]*([0-9 .,]+).*"), price_box)[0].strip()
            price = extract_price(price)

        tax = hxs.select('//span[@class="weee"]/small/text()').extract()
        tax = extract_price(tax[0]) if tax else 0

        if not name:
            name = hxs.select('//div[@class="product-name"]/h1[@itemprop="name"]/text()').extract()

        l = ProductLoader(item=Product(), response=response)
        l.add_xpath('identifier', '//form[@id="product_addtocart_form"]//input[@name="product"]/@value')
        l.add_value('name', name)
        l.add_value('category', category)
        l.add_xpath('brand', '//div[@class="product-manufacturer"]/a/@title')
        l.add_value('sku', sku)
        l.add_value('url', response.url)
        l.add_value('price', price + tax)
        l.add_value('stock', 1)
        l.add_xpath('image_url', '//p[@class="product-image"]/a/img/@src')
        yield l.load_item()

    def parse_product_options(self, response):
        hxs = HtmlXPathSelector(response)

        sku = hxs.select('//p[@class="alignright"]/text()').extract()[0].replace('[', '').replace(']', '')
        category = hxs.select('//div[@class="breadcrumbs"]/ul/li/a/text()').extract()[-1]

        options = hxs.select("//table[@id='super-product-table']/tbody/tr")

        for opt in options:
            opt_identifier = opt.select("td[3]/input/@name").re('super_group\[(.*)\]')[0]
            opt_name = opt.select("td[1]/b[1]/text()").extract()
            opt_price = opt.select(".//span[contains(@id, 'price-excluding-tax-')]/text()").re(r'([0-9\.\, ]+)')[0]

            l = ProductLoader(item=Product(), response=response)
            l.add_xpath('identifier', opt_identifier)
            l.add_value('name', opt_name)
            l.add_value('category', category)
            l.add_xpath('brand', '//div[@class="product-manufacturer"]/a/@title')
            l.add_value('sku', sku)
            l.add_value('url', response.url)
            l.add_value('price', opt_price)
            l.add_value('stock', 1)
            l.add_xpath('image_url', '//p[@class="product-image"]/a/img/@src')
            yield l.load_item()

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return

        # categories
        hxs = HtmlXPathSelector(response)
        category_urls = hxs.select('//ul[@id="mainleftmenu"]//li/a/@href').extract()
        for url in category_urls:
            yield Request(url)

        # subcategories
        subcategory_urls = hxs.select('//div[@class="category-elt"]/p/a/@href').extract()
        for url in subcategory_urls:
            yield Request(url)

        # next page
        next_pages = hxs.select('//div[@class="pages"]/ol//li/a/@href').extract()
        if next_pages:
            for page in next_pages:
                yield Request(page)

        # products
        for p in self.parse_products(response):
            yield p

