# -*- coding: utf-8 -*-

from scrapy import Spider, Request
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from scrapy.utils.url import url_query_parameter, add_or_replace_parameter


class PharmacyfirstSpider(Spider):
    name = u'merckgroup-pharmacyfirst.co.uk'
    allowed_domains = ['www.pharmacyfirst.co.uk']
    start_urls = ('http://www.pharmacyfirst.co.uk/', )

    def parse(self, response):
        for url in response.xpath('//*[@id="nav"]/li//@href').extract():
            yield Request(response.urljoin(url), callback=self.parse_products_list)

    def parse_products_list(self, response):
        products = response.xpath('//div[contains(@class, "card--product")]')
        for product in products:
            presc = ' '.join(product.xpath('.//div[@class="links_widget"]/p/a/span/text()').extract())
            if 'I Have a Private Prescription' in presc or 'I Need a Private Prescription' in presc or 'I Have an NHS Prescription' in presc:
                continue
            loader = ProductLoader(item=Product(), selector=product)
            name = product.xpath('.//h2/a/text()').extract()[0]
            loader.add_value('name', name)
            url = product.xpath('.//h2/a/@href').extract()[0]
            loader.add_value('url', url)
            identifier = product.xpath('.//div/button/@data-product-id').extract()[0]
            loader.add_value('identifier', identifier)
            loader.add_value('sku', identifier)
            price = product.xpath('.//span[@class="special-price"]/span[@class="price"]/text()').extract()
            if not price:
                price = product.xpath('.//span[@class="regular-price"]/span[@class="price"]/text()').extract()
            price = extract_price(price[0])
            loader.add_value('price', price)
            category = response.xpath('//nav[@class="breadcrumb"]//li/span/text()').extract()
            category = category[-1] if category else ''
            loader.add_value('category', category)
            if price < 40:
                loader.add_value('shipping_cost', 3.19)
            image_url = product.xpath('.//img[contains(@id, "product-collection-image")]/@src').extract()
            image_url = response.urljoin(image_url[0]) if image_url else ''
            loader.add_value('image_url', image_url)
            yield loader.load_item()

        url_list = products.xpath('.//h2/a/@href').extract()
        if products and url_list != response.meta.get('url_list', []):
            current_page = url_query_parameter(response.url,'p', '1')
            next_url = add_or_replace_parameter(response.url, 'infinitescroll', '1')
            next_url = add_or_replace_parameter(next_url, 'p', str(int(current_page)+1))
            yield Request(next_url, callback=self.parse_products_list, meta={'url_list': url_list})
