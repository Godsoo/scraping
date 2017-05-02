# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc
from decimal import Decimal


class SupplementcentreSpider(BaseSpider):
    name = u'usn-supplementcentre.com'
    allowed_domains = ['supplementcentre.com']
    start_urls = ['http://www.supplementcentre.com/']

    def start_requests(self):
        brands = {'Optimum Nutrition': 'http://www.supplementcentre.com/shop.cfm/brand/Optimum-Nutrition/showall/1',
                  'BSN': 'http://www.supplementcentre.com/shop.cfm/brand/BSN/showall/1',
                  'PhD': 'http://www.supplementcentre.com/shop.cfm/brand/PHD-Nutrition/showall/1',
                  'Maxi Nutrition': 'http://www.supplementcentre.com/shop.cfm/brand/MaxiNutrition/showall/1',
                  'Reflex': 'http://www.supplementcentre.com/shop.cfm/brand/Reflex-Nutrition/showall/1',
                  'USN': 'http://www.supplementcentre.com/shop.cfm/brand/USN/showall/1'
        }
        for brand, brand_url in brands.items():
            yield Request(brand_url, meta={'brand': brand})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # products
        for url in hxs.select('//a[@class="prodTitle"]/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        image_url = hxs.select('//*[@id="zoomImage"]/@src').extract()
        product_identifier = hxs.select('//input[@name="shopListrec"]/@value').extract()[0].strip()
        product_name = hxs.select('//h1[contains(@class, "prodTitle")]/text()').extract()[0]
        category = hxs.select('//p[@class="crumbsDN"]//a/span/text()').extract()
        brand = response.meta.get('brand')
        price = Decimal(response.xpath('//meta[@itemprop="price"]/@content').extract_first())
        sku = hxs.select('//span[@itemprop="productID"]/text()').extract()[0]
        out_of_stock = hxs.select('//*[@id="errorMsg"]/text()').extract()

        options = hxs.select('//*[@id="options"]//select/option')
        if len(options) > 1:
            self.log('More options!! {}'.format(response.url))
        if options:
            for option in options[1:]:
                identifier = option.select('./@value').extract()[0]
                option_name = option.select('./text()').extract()[0].split('-')[0].strip()
                out_of_stock = option.select('./@disabled').extract()
                product_loader = ProductLoader(item=Product(), selector=hxs)
                product_loader.add_value('identifier', product_identifier + '_' + identifier)
                product_loader.add_value('name', product_name + ' ' + option_name)
                if image_url:
                    product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))

                product_loader.add_value('price', price)
                product_loader.add_value('url', response.url)
                product_loader.add_value('brand', brand)
                product_loader.add_value('category', category)
                product_loader.add_value('sku', sku)
                if price < 75:
                    product_loader.add_value('shipping_cost', 3.99)
                if out_of_stock:
                    product_loader.add_value('stock', 0)
                product = product_loader.load_item()
                yield product
        else:
            product_loader = ProductLoader(item=Product(), selector=hxs)
            product_loader.add_value('identifier', product_identifier)
            product_loader.add_value('name', product_name)
            if image_url:
                product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            product_loader.add_value('price', price)
            product_loader.add_value('url', response.url)
            product_loader.add_value('brand', brand)
            product_loader.add_value('category', category)
            product_loader.add_value('sku', sku)
            if price < 75:
                product_loader.add_value('shipping_cost', 3.99)
            if out_of_stock and out_of_stock == 'OUT OF STOCK':
                product_loader.add_value('stock', 0)
            product = product_loader.load_item()
            yield product
