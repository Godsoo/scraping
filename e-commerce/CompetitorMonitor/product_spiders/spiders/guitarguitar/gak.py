# -*- coding: utf-8 -*-
"""
Gak spider for GuitarGuitar, the spider extracts all the items
Original ticket: https://www.assembla.com/spaces/competitormonitor/tickets/4597-guitar-guitar-%7C-gak-%7C-new-spider/details
"""
import re
import json

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from urlparse import urljoin as urljoin_rfc
from product_spiders.utils import extract_price


class GakCoUkSpider(BaseSpider):
    name = u'guitarguitar-gak.co.uk'
    allowed_domains = ['gak.co.uk']
    start_urls = ('http://www.gak.co.uk/',)

    get_products_url = 'https://www.gak.co.uk/Search/GetProducts'
    crawled_pages = []

    def parse(self, response):
        if response.url.endswith('.pdf') or response.url.startswith('http://www.gak.co.uk/en/%'):
            return

        for url in response.xpath('//li[a[contains(text(), "Guitars & Effects")]]//a/@href').extract():
            yield Request(response.urljoin(url),
                          callback=self.parse_product_list,
                          meta={'category': 'Guitars'})
        for url in response.xpath('//li[a[contains(text(), "Amplifiers")]]//a/@href').extract():
            yield Request(response.urljoin(url),
                          callback=self.parse_product_list,
                          meta={'category': 'Amplifiers'})
        for url in response.xpath('//li[a[contains(text(), "Pro-Audio")]]//a/@href').extract():
            yield Request(response.urljoin(url),
                          callback=self.parse_product_list,
                          meta={'category': 'Pro-Audio'})
        for url in response.xpath('//li[a[contains(text(), "Drum")]]//a/@href').extract():
            yield Request(response.urljoin(url),
                          callback=self.parse_product_list,
                          meta={'category': 'Drums'})
        for url in response.xpath('//li[a[contains(text(), "PA & Live Sound")]]//a/@href').extract():
            yield Request(response.urljoin(url),
                          callback=self.parse_product_list,
                          meta={'category': 'Live Sound'})
        for url in response.xpath('//li[a[contains(text(), "Accessories")]]//a/@href').extract():
            yield Request(response.urljoin(url),
                          callback=self.parse_product_list,
                          meta={'category': 'Accesories'})

    def parse_product_list(self, response):
        if response.url.endswith('.pdf'):
            return

        # try to extract categories links
        categories = response.xpath('//div[@id="content"]/a[@title]/@href').extract()
        categories += response.xpath('//div[contains(@class, "shopByContainer")]//a/@href').extract()
        for url in categories:
            yield Request(response.urljoin(url),
                          callback=self.parse_product_list,
                          meta=response.meta)

        # extract products links
        products = response.xpath('//div[contains(@class, "prod-element")]/a/@href').extract()
        for url in response.xpath('//div[contains(@class, "prod-element")]/a/@href').extract():
            yield Request(response.urljoin(url),
                          callback=self.parse_product,
                          meta=response.meta)

        pages = response.xpath('//div[@class="productListPagination"]//a/@myid').extract()
        for page in pages:
            formdata = {'operation': 'filterProducts',
                        'orderBy': 'ALPHABETICAL',
                        'page': page}

            crawled_page = response.url + page
            if crawled_page not in self.crawled_pages:
                self.crawled_pages.append(crawled_page)
                req = FormRequest(response.url, dont_filter=True, formdata=formdata, callback=self.parse_product_list, meta=response.meta)
                yield req

        for item in self.parse_product(response):
            yield item

    def parse_pages(self, response):
        base_url = "https://www.gak.co.uk/en/"

        data = response.meta['data']

        json_data = json.loads(response.body) 
        products = json_data['Products']
        for product in products:
            yield Request(urljoin_rfc(base_url, product['Url']), callback=self.parse_product)

        total_pages = (json_data['TotalProducts'] / 20) + 1
        if total_pages and not response.meta.get('ignore_pages', False):
            for page in range(total_pages):
                data['page'] = page + 1
  
                req = FormRequest(self.get_products_url, method='POST', dont_filter=True, 
                                  body=json.dumps(data), callback=self.parse_pages, 
                                  meta={'data': data, 
                                        'category_url': response.meta['category_url'],
                                        'ignore_pages': True})
                req.headers['Content-Type'] = 'application/json;charset=utf-8'
                req.headers['X-Requested-With'] = 'XMLHttpRequest'
                yield req
      
    def parse_product(self, response):
        if response.url.endswith('.pdf'):
            return

        loader = ProductLoader(item=Product(), response=response)
        name = ''.join(response.xpath('//div/h1[@class="product-main-title"]/text()').extract())
        if not name:
            return
        loader.add_value('name', name)
        try:
            identifier = response.xpath('//script/text()').re('google_base_offer_id", *"(.+)"')[0] + '-'
        except IndexError:
            identifier = ''
        identifier += response.xpath('//span[@itemprop="productID"]/text()').extract_first()
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        loader.add_value('url', response.url)
        image_url = response.xpath('//meta[@property="og:image"]/@content').extract()
        if image_url:
            loader.add_value('image_url', response.urljoin(image_url[0]))
        price = response.xpath('//span[contains(@class, "gak-price")]/text()').extract()
        price = extract_price(price[0]) if price else 0
        loader.add_value('price', price)
        brand = response.xpath('//a[@id="brandCategorySearch"]/text()').re('View all (.*)')
        if brand:
            brand = brand[0].rpartition('-')[0]
            loader.add_value('brand', brand)
        category = response.meta.get('category')
        if category:
            loader.add_value('category', category)
        else:
            loader.add_value('category', brand)
        yield loader.load_item()

        for url in response.xpath('//ul[contains(@class, "dropdown-menu")]//a/@href').extract():
            yield Request(response.urljoin(url),
                          callback=self.parse_product,
                          meta=response.meta)
