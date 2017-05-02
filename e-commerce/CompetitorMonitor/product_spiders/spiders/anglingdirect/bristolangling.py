import re
import os

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

import csv

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader


class BristolAnglingSpider(BaseSpider):
    name = 'bristolangling.com'
    allowed_domains = ['bristolangling.com']
    start_urls = ('http://www.bristolangling.com/',)

    stock_url = 'http://www.bristolangling.com/stock/?id={}'

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        # categories
        categories = response.xpath('//*[@id="nav"]//a/@href').extract()
        for url in categories:
            if url.endswith('blog'):
                continue
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)

        # pages
        next_page = response.xpath(u'//a[@class="next i-next"]/@href').extract()
        if next_page:
            url = urljoin_rfc(get_base_url(response), next_page[0])
            yield Request(url, callback=self.parse_category)

        # products
        products = response.xpath(u'//h2[@class="product-name"]/a/@href').extract()
        for url in products:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product)

        if not products:
            meta = response.meta.copy()
            meta['retry'] = meta.get('retry', 0)
            if meta['retry'] < 10:
                meta['retry'] += 1
                self.log('>>> RETRY %d => %s' % (meta['retry'], response.request.url))
                yield Request(response.request.url, meta=meta)

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return

        hxs = HtmlXPathSelector(response)
        brand = response.xpath('//tr[contains(th/text(), "Brand")]/td/text()').extract()
        brand = brand[0] if brand else ''
        category = response.xpath(u'//div[@class="breadcrumbs"]//a/text()').extract()
        category = category[-1] if category else ''
        image_url = response.xpath(u'//img[@id="image-main"]/@src').extract()
        if image_url:
            image_url = urljoin_rfc(get_base_url(response), image_url[0])

        name = response.css('div.product-name h1::text').extract_first()

        multiple_prices = response.xpath(u'//table[@id="super-product-table"]/tbody/tr')
        if not multiple_prices:
            product_loader = ProductLoader(item=Product(), response=response)
            product_loader.add_value('name', name)
            product_loader.add_value('url', response.url)
            product_loader.add_value('brand', brand)
            product_loader.add_value('category', category)
            product_loader.add_value('image_url', image_url)
            identifier = response.xpath('.//span/@id').re('product-price-(.+)')[0]
            product_loader.add_value('identifier', identifier)
            product_loader.add_xpath('price', u'//div[@class="price-box"]/span[contains(@id,"product-price")]/span[@class="price"]/text()',
                                     re='\xa3(.*[0-9])')
            product_loader.add_xpath('price', u'//div[@class="price-box"]/p[@class="special-price"]/span[@class="price"]/text()',
                                     re='\xa3(.*[0-9])')
            product = product_loader.load_item()
            yield Request(self.stock_url.format(product['identifier']), meta={'product': product}, callback=self.parse_stock)
        else:
            for name_and_price in multiple_prices:
                product_loader = ProductLoader(item=Product(), selector=name_and_price)
                name_options = name_and_price.select(u'./td[position()=1]/text()').extract()[0]
                product_loader.add_value('name', name + ' ' + name_options)
                product_loader.add_value('url', response.url)
                product_loader.add_xpath('price', u'./td[position()=2]/div[@class="price-box"]/span[@class="regular-price"]/span[@class="price"]/text()',
                                         re=u'\xa3(.*)')
                product_loader.add_xpath('price', u'./td[position()=2]/div[@class="price-box"]/p[@class="special-price"]/span[@class="price"]/text()',
                                         re=u'\xa3(.*)')
                identifier = name_and_price.xpath(u'.//span/@id').re('product-price-(.+)')[0]
                product_loader.add_value('brand', brand)
                product_loader.add_value('category', category)
                product_loader.add_value('image_url', image_url)
                product_loader.add_value('identifier', identifier)
                product = product_loader.load_item()
                yield Request(self.stock_url.format(product['identifier']), meta={'product': product}, callback=self.parse_stock)

    def parse_stock(self, response):
        product = response.meta.get('product')
        if not '1' in response.body:
            product['stock'] = 0
        yield product
