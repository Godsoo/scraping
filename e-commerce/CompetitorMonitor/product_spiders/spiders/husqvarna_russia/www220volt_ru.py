# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector, Selector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy import log


class www220voltRuSpider(BaseSpider):
    name = u'www220volt_ru'
    allowed_domains = ['220-volt.ru']
    start_urls = [
        'http://www.220-volt.ru/catalog/'
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        #items =  hxs.select('//div[@id="cat-2"]//li/a/@href').extract()
        items = hxs.select('//div[@class="group-list-item"]//li/a/@href').extract()
        if items:
            log.msg("Cat items " + str(len(items)))
            for url in items:
                yield FormRequest(urljoin_rfc(base_url, url), formdata={'limit': '10000'}, callback=self.parse_products_list)

    def parse_products_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        category = ''.join(hxs.select('//h1[@id="h1"]/text()').extract()).strip()
        items = hxs.select('//div[contains(@class, "new-items-list")]//div[@class="new-item-list-name"]/a/@href').extract()
        if items:
            log.msg(response.url + " Pdtcs: " + str(len(items)))
            for url in items:
                yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta={'category': category})
                
        pages = response.css('.pager a::attr(href)').extract()
        for url in pages:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list)

    def parse_product(self, response):
        pd = Selector(response)
        url = response.url
        category = response.meta['category']
        image_url = pd.select('//a[@id="zoom1"]/@href').extract()
        product_identifier = response.xpath('//@data-code').extract()
        product_identifier = response.xpath('//span[@id="product-code"]/span/strong/text()').extract()
        if not product_identifier:
            product_identifier = response.xpath('//span[@id="product-code"]/text()').extract()
        if not product_identifier:
            log.msg(url + " no Code/ID")
        product_identifier = product_identifier[0].strip()
        product_name = pd.select('//h1[@itemprop="name"]/text()').extract()[0].strip()
        brands = response.css('ul.breadcrumbsList li').xpath('.//a[contains(@href, "/producer/")]/text()').extract()
        if not brands:
            brands = pd.select('//div[@class="modelContainer"]//li[@class="first"]/a/text()').extract()
        brand = ''
        if brands:
            brand = brands[0].strip()
        else:
            log.msg(url + " no BRND")

        product_loader = ProductLoader(item=Product(), selector=pd)
        product_loader.add_value('identifier', product_identifier)
        product_loader.add_value('name', product_name)
        product_loader.add_value('sku', product_identifier)
        if image_url:
            product_loader.add_value('image_url', image_url[0])
        price = response.xpath('//script/text()').re('product_price":(.+?),')
        if not price:
            price = response.xpath('//span[@id="price_per_m"]/text()').extract()
        price = price[0] if price else 0
        product_loader.add_value('price', price.strip().replace(" ",""))
        product_loader.add_value('url', url)
        product_loader.add_value('brand', brand)
        product_loader.add_value('category', category)
        product = product_loader.load_item()
        yield product
