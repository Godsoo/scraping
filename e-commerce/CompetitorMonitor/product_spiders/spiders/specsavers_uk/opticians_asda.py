# -*- coding: utf-8 -*-


"""
Account: SpecSavers UK
Name: specsavers_uk-opticians.asda.com
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4544
Original developer: Emiliano M. Rudenick <emr.frei@gmail.com>
"""


from scrapy import Spider, Request
from scrapy.utils.url import add_or_replace_parameter
from product_spiders.items import (
    ProductLoaderWithNameStrip as ProductLoader,
    Product,
)
from urllib import unquote


class TescoOpticians(Spider):
    name = 'specsavers_uk-opticians.asda.com'
    allowed_domains = ['asda.com']

    start_urls = [
        'https://opticians.asda.com/Contact-lenses',
        'https://opticians.asda.com/Solution-and-eye-care',
        'https://opticians.asda.com/Prescription-Glasses',
    ]

    def parse(self, response):
        for url in response.xpath('//li[@id="ViewAll"]/a/@href').extract():
            yield Request(response.urljoin(url))

        categories = response.xpath('//ul[@class="BreadcrumbNav"]//a/text()').extract()[1:]
        urljoin_lmb = lambda u: response.urljoin(u[0])
        products = response.xpath('//ul[@class="ProductInfo"]')
        for product_xs in products:
            price_found = bool(product_xs.xpath('.//li[@id="DisplayPrice"]/text()'))
            product_url = product_xs.xpath('.//li[@id="DisplayText"]/a/@href').extract()[0]
            product_url = response.urljoin(product_url)
            identifier = product_url.split('/')[-1].lower()
            brand = unquote(product_url.split('/')[-2]).replace('-', ' ')

            loader = ProductLoader(item=Product(), selector=product_xs)
            loader.add_value('identifier', identifier)
            loader.add_xpath('name', './/li[@id="DisplayText"]//text()')
            loader.add_value('url', product_url)
            loader.add_xpath('image_url', './/li[@id="Image"]//img/@src', urljoin_lmb)
            loader.add_value('category', categories)
            loader.add_value('brand', brand)

            if price_found:
                loader.add_xpath('price', './/li[@id="DisplayPrice"]', re=r'[\d,\.]+')
                yield loader.load_item()
            else:
                product_item = loader.load_item()
                yield Request(product_url,
                              callback=self.parse_product,
                              meta={'product': product_item})

        if len(products) == 15:
            page_no = int(response.meta.get('page_no', 1)) + 1
            url = add_or_replace_parameter(response.url, 'page', str(page_no))
            yield Request(url, meta={'page_no': page_no})

    def parse_product(self, response):
        product = response.meta['product']
        price = response.xpath('//*[@id="glasses-right-col1"]/img/@alt').re(r'[\d\,.]+')
        if not price:
            price = '0.00'
        loader = ProductLoader(item=product, response=response)
        loader.add_value('price', price)
        yield loader.load_item()
