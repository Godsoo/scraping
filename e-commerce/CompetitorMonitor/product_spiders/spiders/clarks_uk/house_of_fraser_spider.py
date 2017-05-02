# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy.http import Request

from decimal import Decimal


class HouseOfFraserSpider(BaseSpider):
    name = 'house_of_fraser'
    start_urls = ['http://www.houseoffraser.co.uk/Dune+Shoes+Boots/BRAND_DUNE_15,default,sc.html?sz=300',
                  'http://www.houseoffraser.co.uk/Dune+Bags+Luggage/BRAND_DUNE_17,default,sc.html?sz=300',
                  'http://www.houseoffraser.co.uk/Dune+Accessories/BRAND_DUNE_16,default,sc.html?sz=300',
                  'http://www.houseoffraser.co.uk/Dune+Men/BRAND_DUNE_02,default,sc.html?sz=300',
                  'http://www.houseoffraser.co.uk/Ecco/BRAND_ECCO,default,sc.html?fromBrand=Ecco?sz=300',
                  'http://www.houseoffraser.co.uk/Dune+Black/BRAND_DUNE%20BLACK,default,sc.html?fromBrand=Dune%20Black',
                  'http://www.houseoffraser.co.uk/Bertie/BRAND_BERTIE,default,sc.html?fromBrand=Bertie',
                  'http://www.houseoffraser.co.uk/Head+Over+Heels/BRAND_HEAD%20OVER%20HEELS,default,sc.html?fromBrand=Head%20Over%20Heels',
                  'http://www.houseoffraser.co.uk/Pied+a+Terre/BRAND_PIED%20A%20TERRE,default,sc.html?fromBrand=Pied%20a%20Terre']

    identifiers = {}

    def parse(self, response):

        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//div[contains(@class, "product-description")]/a/@href').extract():
            yield Request(url, callback=self.parse_item)

        next_page = hxs.select('//a[contains(@class, "pager") and contains(@class, "nextPage")]/@href').extract()
        if next_page:
            yield Request(url=next_page[0], callback=self.parse, dont_filter=True)

    def parse_item(self, response):

        hxs = HtmlXPathSelector(response)

        categories = hxs.select('//ol[@class="hof-breadcrumbs clearfix pdp_breadcrumbs"]//a[@itemprop="breadcrumb"]/text()').extract()[-2:]
        add_cat = hxs.select('//*[@id="psiTab1"]/div/div[2]/span/ul/li[1]/text()').extract()
        if add_cat:
            categories.append(add_cat[0])

        options = hxs.select('//ul[@class="size-swatches-list toggle-panel"]/li').extract()
        for option in options:
            if 'disabled' not in option:
                product_stock = 1
                break
        else:
            product_stock = 0

        if 'this item is not available' in response.body:
            product_stock = 0

        product_sku = ''.join(hxs.select('//div[@class="product-code"]/text()').extract()).strip().replace(
            'Product code:', '').strip()

        product_name = ' '.join(filter(lambda s: s, map(unicode.strip, hxs.select(
            '//div[@class="title-ratings-block"]//text()').extract()))).strip()
        product_brand = ''.join(
            hxs.select('//div[@class="title-ratings-block"]//span[@class="brandname"]/text()').extract()).strip()
        product_image = hxs.select('//img[contains(@class, "featuredProductImage")]/@src').extract()

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('name', product_name)
        loader.add_value('image_url', product_image)
        loader.add_value('url', response.url)
        loader.add_xpath('price', '//meta[@itemprop="price"]/@content')
        loader.add_value('stock', product_stock)
        loader.add_value('brand', product_brand)
        loader.add_value('identifier', product_sku)
        loader.add_value('sku', product_sku)

        product_price = loader.get_output_value('price')
        if product_price:
            shipping_cost = '3.0' if product_price < Decimal('50') else '0'
            loader.add_value('shipping_cost', shipping_cost)

        categories.insert(0, product_brand)
        loader.add_value('category', categories)

        yield loader.load_item()
