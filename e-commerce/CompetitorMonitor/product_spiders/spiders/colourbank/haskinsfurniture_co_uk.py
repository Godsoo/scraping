"""
Name: colourbank-haskinsfurniture.co.uk
Account: Colourbank
"""

import re

from scrapy.selector import HtmlXPathSelector

try:
    from scrapy.spiders import Spider as BaseSpider
except ImportError:
    from scrapy.spider import BaseSpider

from scrapy.http import Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin as urljoin_rfc
from product_spiders.utils import extract_price

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class CBHaskinsFurnitureCoUkSpider(BaseSpider):
    name = 'colourbank-haskinsfurniture.co.uk'
    allowed_domains = ['haskinsfurniture.co.uk']
    start_urls = ['http://www.haskinsfurniture.co.uk/index.php?subcats=Y&status=A&pshort=Y&pfull=Y&pname=Y&pkeywords=Y&search_performed=Y&hint_q=Search+products&dispatch=products.search&items_per_page=96']

    rotate_agent = True

    def parse(self, response):
        base_url = get_base_url(response)

        for url in response.xpath('//div[@class="grid-list"]/div//div[contains(@class, "name")]/a/@href').extract():
            url = urljoin_rfc(base_url, url)
            yield Request(url, callback=self.parse_product, meta={'dont_merge_cookies': True})

        for url in response.xpath('//*[@id="pagination_contents"]//a/@href').extract():
            url = urljoin_rfc(base_url, url)
            yield Request(url, callback=self.parse, meta={'dont_merge_cookies': True})


    def parse_product(self, response):
        base_url = get_base_url(response)

        product_loader = ProductLoader(item=Product(), response=response)

        product_loader.add_value('url', response.url)
        name = response.xpath('//h1[contains(@class, "ty-product-block-title")]/text()').extract()[0]
        product_loader.add_value('name', name)
        category = response.xpath('//*[@id="breadcrumbs_1"]//a/text()').extract()[1:]
        product_loader.add_value('category', category)
        brand = re.findall("'brand': '(.*)'", response.body)
        brand = brand[0].strip() if brand else ''
        product_loader.add_value('brand', brand)
        sku = response.xpath('//div[@class="ty-product-feature"]/span[contains(text(), "Model Code:")]/../div[@class="ty-product-feature__value"]/text()').extract()
        if sku:
            sku = '' if sku[0] == u'.' else sku
            product_loader.add_value('sku', sku)
        img = response.xpath('//div[contains(@id, "product_images")]//img[contains(@id, "det_img_")]/@src').extract()
        if img:
            product_loader.add_value('image_url', urljoin_rfc(base_url, img.pop()))
        product = product_loader.load_item()

        options = response.xpath('//div[@class="ty-compact-list__item"]')

        if not options:
            prod = Product(product)
            product_identifier = response.xpath('//script/text()').re("'id':\s*'(.+)'")[0]
            prod['identifier'] = product_identifier
            price = response.xpath('//div[@id="product-right"]//div[@class="now-price"]/span[@class="price"]/text()').extract()
            if not price:
                price = response.xpath('//script/text()').re("'price':\s*'(.+)'")

            price = price[0] if price else ''
            price = extract_price(price)
            prod['price'] = price
            yield prod

        else:
            for option in options:
                prod = Product(product)
                product_identifier = option.xpath('.//div[contains(@id,"add_to_cart_update_")]/@id').extract()[0]
                product_identifier = product_identifier.replace('add_to_cart_update_', '')
                opt_name = option.xpath('.//h3/text()').extract()
                opt_name = opt_name[0].replace('Upgrade Promotion', '').strip() if opt_name else ''
                price = option.xpath('.//span[@class="ty-price-num"]/@id/../text()').extract()
                price = extract_price(price[0]) if price else 0
                prod['price'] = price
                prod['name'] += ' ' + opt_name
                prod['identifier'] = product_identifier
                yield prod
