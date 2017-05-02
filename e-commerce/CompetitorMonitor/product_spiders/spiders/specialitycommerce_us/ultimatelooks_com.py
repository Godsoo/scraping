# -*- coding: utf-8 -*-

from scrapy import Spider, Request
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price


class UltimatelooksComSpider(Spider):
    name = u'specialitycommerce_us-ultimatelooks.com'
    allowed_domains = ['ultimatelooks.com']
    start_urls = ['http://www.ultimatelooks.com/']

    product_ids = []

    def parse(self, response):
        # categories
        urls = response.xpath('//ul[@id="drop-nav"]//a/@href').extract()
        categories = map(lambda s: ' '.join(s.split()).strip(), response.xpath('//ul[@id="drop-nav"]//a/text()').extract())
        for url, category in zip(urls, categories):
            yield Request(response.urljoin(url),
                          callback=self.parse_categories,
                          meta={'category': category})

    def parse_categories(self, response):
        category = response.meta.get('category', '')
        # products
        for url in response.xpath('//table[@id="table19" or @id="table17" or @id="table21" or @id="table22"]//a/@href').extract():
            if url.endswith('.jpg'):
                continue
            yield Request(response.urljoin(url), callback=self.parse_product, meta={'category': category})
        # pages
        for url in response.xpath('//a[@title="Next"]/@href').extract():
            yield Request(response.urljoin(url), callback=self.parse_categories, meta={'category': category})

    def parse_product(self, response):
        identifier = response.xpath('//input[@name="key"]/@value').extract()
        if not identifier:
            return
        identifier = identifier[0]

        product_name = response.xpath('//h1//span/text()').extract()
        if not product_name:
            product_name = response.xpath('//title/text()').extract()[0].split('by')[0].strip()
        else:
            product_name = product_name[0]

        image_url = response.xpath('/html/body/table/tr[3]/td/table/tr/td[2]/table[1]/tbody/tr/td[1]/p[1]/img/@src').extract()
        if not image_url:
            image_url = response.xpath('/html/body/table/tr[3]/td/table/tr/td[2]/table[2]/tbody/tr/td[1]/p[1]/img/@src').extract()
        if not image_url:
            image_url = response.xpath('/html/body/table/tr[3]/td/table/tr/td[2]/table[1]/tbody/tr/td[1]/p[1]/font/img/@src').extract()
        if not image_url:
            image_url = response.xpath('/html/body/table/tr[3]/td/table/tr/td[2]/table[2]/tbody/tr/td[1]/p[1]/font/img/@src').extract()
        if not image_url:
            image_url = response.xpath('/html/body/table/tr[3]/td/table/tr/td[2]/table[2]/tr/td[1]/p[1]/img/@src').extract()
        if not image_url:
            image_url = response.xpath('/html/body/table/tr[3]/td/table/tr/td[2]/table[2]/tbody/tr/td[1]/p[2]/font/img/@src').extract()
        if not image_url:
            image_url = response.xpath('/html/body/table/tr[3]/td/table/tr/td[2]/table[2]/tbody/tr/td[1]/p[2]/img/@src').extract()

        price = response.xpath('//span[contains(text(), "$")]/text()').extract()
        if not price or len(price[0]) > 10:
            price = response.xpath('//font[contains(text(), "$")]/text()').extract()
            if not price:
                price = response.xpath('//font/strong[contains(text(), "$")]/text()').extract()
        price = extract_price(price[0])
        category = response.meta.get('category', '')

        brand = response.xpath('//title/text()').extract()[0]
        if 'by' in brand:
            brand = brand.split('by')[1].strip()
        elif 'BY' in brand:
            brand = brand.split('BY')[1].strip()
        elif '-' in brand:
            brand = brand.split('-')[1].strip()
        else:
            brand = ''
        brand = brand.split('|')[0].strip()
        brand = brand.replace(':', '').strip()

        sku = identifier

        options = response.xpath('//select[@name="opt0"]//option')
        if options:
            for option in options[1:]:
                opt_id = option.xpath('./@value').extract()[0]
                opt_name = option.xpath('./text()').extract()[0]
                if '$' in opt_name:
                    add_price = extract_price(opt_name)
                    opt_name = opt_name.split('(')[0].strip()
                else:
                    add_price = extract_price('0')
                product_identifier = identifier + '_' + opt_id
                if product_identifier in self.product_ids:
                    continue
                else:
                    self.product_ids.append(product_identifier)
                name = product_name + ' ' + opt_name
                loader = ProductLoader(item=Product(), response=response)
                loader.add_value('identifier', product_identifier)
                loader.add_value('sku', sku)
                loader.add_value('url', response.url)
                loader.add_value('name', name)
                loader.add_value('shipping_cost', 6)
                loader.add_value('price', price + add_price)
                if image_url:
                    loader.add_value('image_url', response.urljoin(image_url[0]))
                loader.add_value('category', category)
                loader.add_value('brand', brand)
                yield loader.load_item()
        else:
            only_color = response.xpath('//span[normalize-space(text())="Color Available"]/../span[last()]/text()').re('\S+')
            if only_color and len(only_color) == 1:
                product_name += ' ' + only_color[0]
            loader = ProductLoader(item=Product(), response=response)
            if identifier in self.product_ids:
                return
            else:
                self.product_ids.append(identifier)
            loader.add_value('identifier', identifier)
            loader.add_value('sku', sku)
            loader.add_value('url', response.url)
            loader.add_value('name', product_name)
            loader.add_value('shipping_cost', 6)
            loader.add_value('price', price)
            if image_url:
                loader.add_value('image_url', response.urljoin(image_url[0]))
            loader.add_value('category', category)
            loader.add_value('brand', brand)
            yield loader.load_item()
