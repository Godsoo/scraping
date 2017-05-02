# -*- coding: utf-8 -*-
import urlparse
from decimal import Decimal
import re
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from product_spiders.utils import extract_price
from fragrancedirectitem import FragranceDirectMeta


class TheperfumeshopSpider(BaseSpider):
    name = 'theperfumeshop'
    allowed_domains = ['theperfumeshop.com']
    start_urls = [
        'http://www.theperfumeshop.com/',
        # 'http://www.theperfumeshop.com/pws/ProductDetails.ice?ProductID=7587'
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        # we extract the categories urls
        categories = hxs.select("//div[@class='nav-submenu']//@href").extract()
        for category in categories:
            yield Request(
                urlparse.urljoin(get_base_url(response), category),
                callback=self.parse_category
            )

    def parse_category(self, response):
        """
        While parsing a category page we need to look after a product or category list
        """
        hxs = HtmlXPathSelector(response)

        # products
        for product_url in hxs.select("//div[@class='product-tile']//a/@href").extract():
            if 'http' in product_url:
                pass
            else:
                product_url = urlparse.urljoin(get_base_url(response), product_url)
            yield Request(
                product_url,
                callback=self.parse_product
            )

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        for sub_option in response.xpath('//ul[@id="pricegrid"]/li'):
            loader = ProductLoader(item=Product(), response=response)

            price = ''.join(sub_option.select('@data-fprice').extract())
            price = extract_price(price.strip())

            loader.add_value('price', price)
            loader.add_value('url', response.url)

            loader.add_xpath('name', '(//h1//span)[position()<3]/text()')
            option_name = sub_option.xpath('label/input/@value').extract_first()
            loader.add_value('name', option_name)

            if price:
                loader.add_value('stock', '1')
            else:
                loader.add_value('stock', '0')

            loader.add_xpath('category', "//ol[@class='breadcrumbs']//li[1 < position() and position() < last()]//a/span/text()")
            loader.add_xpath('brand', '//img[@class="brand-logo"]/@alt')
            shipping_cost = '0'
            loader.add_value('shipping_cost', shipping_cost)
            sku = ''.join(sub_option.select('@data-code').extract())
            loader.add_value('sku', sku)
            loader.add_value('identifier', sku)
            img = response.xpath('//meta[@property="og:image"]/@content').extract()
            if img:
                img = urlparse.urljoin(get_base_url(response), img[0])

            loader.add_value('image_url', img)

            #gift_metadata = [urlparse.urljoin(get_base_url(response), g) for
            #                 g in hxs.select("//div[@id='productIncentiveCont']//img/@src").extract()]
            #sub_option_metadata = [
            #    re.sub(" {2,}", "", x.strip()) for x
            #    in sub_option.select(".//p[@class='addInfo']//text()").extract() if x.strip()
            #    ]

            #loader.add_value('metadata', {
            #    'gift': gift_metadata,
            #    'product': sub_option_metadata,
            #})
            product = loader.load_item()
            metadata = FragranceDirectMeta()
            if product.get('price'):
                metadata['price_exc_vat'] = Decimal(product['price']) / Decimal('1.2')
            product['metadata'] = metadata
            yield product
