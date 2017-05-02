# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from urlparse import urljoin as urljoin_rfc
from product_spiders.utils import extract_price


class GakCoUkSpider(BaseSpider):
    name = u'decks_gak.co.uk'
    allowed_domains = ['www.gak.co.uk']
    start_urls = ('http://www.gak.co.uk/',)

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        if response.url.endswith('.pdf') or response.url.startswith('http://www.gak.co.uk/en/%'):
            return

        for url in hxs.select('//div[@id="tabs_0d"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_product_list,
                          meta={'category': 'Guitars'})
        for url in hxs.select('//div[@id="tabs_1d"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_product_list,
                          meta={'category': 'Amplifiers'})
        for url in hxs.select('//div[@id="tabs_2d"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_product_list,
                          meta={'category': 'Pro-Audio'})
        for url in hxs.select('//div[@id="tabs_3d"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_product_list,
                          meta={'category': 'Drums'})
        for url in hxs.select('//div[@id="tabs_4d"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_product_list,
                          meta={'category': 'Live Sound'})
        for url in hxs.select('//div[@id="tabs_5d"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_product_list,
                          meta={'category': 'Accesories'})


    def parse_product_list(self, response):

        if response.url.endswith('.pdf') or response.url.startswith('http://www.gak.co.uk/en/%'):
            return

        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        # try to extract categories links
        categories = hxs.select('//div[@id="content"]/a[@title]/@href').extract()
        for url in categories:
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_product_list,
                          meta={'category': response.meta.get('category')})

        # extract products links
        for url in hxs.select('//div[@class="snapshot"]//div[@class="opt"]/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_product,
                          meta={'category': response.meta.get('category')})

        for item in self.parse_product(response):
            yield item

    def parse_product(self, response):
        if response.url.endswith('.pdf') or response.url.startswith('http://www.gak.co.uk/en/%'):
            return

        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        name = ''.join(hxs.select('//*[@id="prodh1"]/text()').extract())
        if not name or 'B-STOCK' in name.upper():
            return
        loader.add_value('name', name)
        identifier = hxs.select('//form[@id="buyoptions"]//input[@name="v[order_id]"]/@value').extract()
        if not identifier:
            identifier = [response.url.split('/')[-1]]
        loader.add_value('identifier', identifier[0].strip())
        loader.add_value('sku', identifier[0].strip())
        loader.add_value('url', response.url)
        image_url = hxs.select('//*[@id="prodphoto"]/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        price = hxs.select('//*[@id="prodprice"]/text()').extract()
        if price:
            price = extract_price(price[0])
            loader.add_value('price', price)
        brand = hxs.select('//*[@id="prodtools"]/ul/li/a/@href').extract()
        if brand:
            brand = brand[0].replace('/en/list/mc/', '').split('/')[0]
            loader.add_value('brand', brand)
        category = response.meta.get('category')
        if category:
            loader.add_value('category', category)
        else:
            loader.add_value('category', brand)
        yield loader.load_item()
        for url in hxs.select('//*[@id="buyoptions"]//select[@name="variation"]/option/@value').extract():
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_product,
                          meta={'category': category})
