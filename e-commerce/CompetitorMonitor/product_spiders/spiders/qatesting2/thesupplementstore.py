# -*- coding: utf-8 -*-
import scrapy
from scrapy.selector import HtmlXPathSelector
from scrapy.spider import BaseSpider
from scrapy.http import HtmlResponse, Request
from scrapy.utils.response import get_base_url
from supplementmeta import SupplementMeta
from decimal import Decimal
from scrapy.utils.url import urljoin_rfc
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class SupplementSpider(BaseSpider):
    name = 'thesupplementstore.co.uk'
    allowed_domains = ['www.thesupplementstore.co.uk']
    start_urls = ['https://www.thesupplementstore.co.uk/brands/sci_mx_nutrition', 'https://www.thesupplementstore.co.uk/brands/optimum_nutrition',
                  'https://www.thesupplementstore.co.uk/brands/bsn', 'https://www.thesupplementstore.co.uk/brands/phd_nutrition',
                  'https://www.thesupplementstore.co.uk/brands/maxinutrition', 'https://www.thesupplementstore.co.uk/brands/reflex_nutrition',
                  'https://www.thesupplementstore.co.uk/brands/mutant', 'https://www.thesupplementstore.co.uk/brands/cellucor',
                  'https://www.thesupplementstore.co.uk/brands/usn']


    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        urls_list = hxs.select('//ol[@class="content grid"]/li')
        for url_list in urls_list:
            link = url_list.select('div[@class="im"]/a/@href').extract()[0]
            yield Request(urljoin_rfc(base_url, link), callback=self.parse_data)
        pagination = hxs.select('//div[@class="pagination"]/a[@class="next"]/@href').extract()
        if pagination:
            yield Request(urljoin_rfc(base_url, pagination[0]), callback=self.parse)


    def parse_data(self, response):
        hxs = HtmlXPathSelector(response)
        metadata = SupplementMeta()
        title = hxs.select('//h1[@itemprop="name"]/text()').extract()[0]
        price_was = hxs.select('/html/head/meta[@property="og:price:standard_amount"]/@content').extract()[0]
        now_price = hxs.select('/html/head/meta[@property="og:price:amount"]/@content').extract()[0]
        metadata['list_price'] = price_was
        if Decimal(now_price) <= 30:
            shipping = '1.99'
        else:
            shipping = '0'
        currency = hxs.select('/html/head/meta[@property="og:price:currency"]/@content').extract()[0]
        sku = hxs.select('/html/head/meta[@name="bc:sku"]/@content').extract()[0]
        category = hxs.select('/html/head/meta[@property="product:category"]/@content').extract()[0].split('>')[-1].strip()
        brand = hxs.select('//div[@class="brand-intro"]//img/@alt').extract()[0]
        variants = hxs.select('//div[@class="variant"]')
        for variant in variants:
            price_comp = variant.select('div[@class="title"]//span[@class="list"]/text()').extract()[0].split(u'\xa3')[-1]
            if Decimal(price_comp) == Decimal(price_was):
                stock_variants = variant.select('table//tr')
                for stock_variant in stock_variants:
                    loader = ProductLoader(item=Product(), response=response)
                    item_variant = stock_variant.select('td[@class="name"]/text()').extract()[0].strip()
                    loader.add_value('name', title+' '+item_variant)
                    loader.add_value('shipping_cost', shipping)
                    loader.add_value('sku', sku)
                    loader.add_value('price', now_price)
                    loader.add_value('identifier', sku+' '+item_variant)
                    loader.add_value('category', category)
                    loader.add_value('brand', brand)
                    loader.add_value('url', response.url)
                    image_url = hxs.select('//div[@id="product-image"]//img/@src').extract()
                    if image_url:
                        image_url = image_url[0]
                    loader.add_value('image_url', image_url)
                    stock = stock_variant.select('td[@class="stock instock"]/text()').extract()
                    if not stock:
                        stock = stock_variant.select('td[@class="stock outofstock"]/text()').extract()
                        loader.add_value('stock', 0)
                    item = loader.load_item()
                    metadata['item_variant'] = item_variant
                    item['metadata'] = metadata
                    yield item