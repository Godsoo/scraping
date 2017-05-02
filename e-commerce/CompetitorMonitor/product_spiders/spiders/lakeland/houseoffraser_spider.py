import os
import re
import json

from scrapy import log
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.base_spiders import PrimarySpider
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class HouseOfFraserSpider(PrimarySpider):
    name = 'lakeland-houseoffraser.co.uk'
    allowed_domains = ['houseoffraser.co.uk', 'houseoffraserkitchenappliances.co.uk']
    csv_file = 'lakeland_houseoffraser_as_prim.csv'
    start_urls = ['http://www.houseoffraser.co.uk/Kitchen+Dining+Accessories+Appliances/503,default,sc.html',
                  'http://www.houseoffraser.co.uk/Basin+Accessories/5046,default,sc.html',
                  'http://www.houseoffraser.co.uk/Toilet+Brushes/5064,default,sc.html',
                  'http://www.houseoffraser.co.uk/Bathroom+Scales/5008,default,sc.html',
                  'http://www.houseoffraser.co.uk/Towels+Bath+Mats/5045,default,sc.html',
                  'http://www.houseoffraser.co.uk/Laundry+Baskets+Storage/5010,default,sc.html',
                  'http://www.houseoffraser.co.uk/Food+Drink/512,default,sc.html',
                  'http://www.houseoffraser.co.uk/Tableware+and+Dining/506,default,sc.html',
                  'http://www.houseoffraser.co.uk/Gifts+For+Home/Giftsforhome,default,pg.html',
                  'http://www.houseoffraser.co.uk/Decorative+Garden/5157,default,sc.html',
                  'http://www.houseoffraser.co.uk/Outdoor+Dining/5155,default,sc.html',
                  'http://www.houseoffraser.co.uk/Irons+Steam+Generators/996,default,sc.html',
                  'http://www.houseoffraser.co.uk/Vacuum+Steam+Cleaners/998,default,sc.html',
                  'http://www.houseoffraser.co.uk/Stand+Mixers/00032,default,sc.html',
                  'http://www.houseoffraser.co.uk/Cooking+Steaming/9973,default,sc.html',
                  'http://www.houseoffraser.co.uk/Food+Processors/00031,default,sc.html',
                  'http://www.houseoffraser.co.uk/Food+Preparation/9974,default,sc.html',
                  'http://www.houseoffraser.co.uk/Kitchen+Electrical+Sets/9978,default,sc.html',
                  'http://www.houseoffraser.co.uk/Kettles/9977,default,sc.html',
                  'http://www.houseoffraser.co.uk/Toasters/9972,default,sc.html',
                  'http://www.houseoffraser.co.uk/Coffee+Machines/9975,default,sc.html',]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        sub_categories = hxs.select('//div[@id="inThisSection"]//li/a/@href').extract()
        for sub_category in sub_categories:
            yield Request(urljoin_rfc(get_base_url(response), sub_category))

        products = hxs.select('//li[@class="product-list-element"]')
        for product in products:
            url = product.select('a/@href').extract()[0]
            brand = ''.join(product.select('div//div[@class="product-description"]/a/h3/text()').extract()).strip()
            yield Request(url, callback=self.parse_product, meta={'brand':brand})

        next = hxs.select('//a[@class="pager nextPage"]/@href').extract()
        if next:
            yield Request(next[0])

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        meta = response.meta

        products = hxs.select('//div[contains(@class, "item-details")]/div/header/h3/a/@href').extract()
        products += hxs.select('//div[contains(@class, "setProduct")]/div/h5/a/@href').extract()
        if products:
            for product in products:
                url = urljoin_rfc(get_base_url(response), product)
                yield Request(url, callback=self.parse_product, meta=meta)
            return

        data = re.search('var _DCSVariables = (.*);</script>', response.body)
        if data:
            data = data.group(1)
            data = json.loads(data)

        category =  hxs.select('//ol[contains(@class, "hof-breadcrumbs")]'
                               '//li[not(@class="home")]/a[@itemprop="breadcrumb"'
                               ' and not(contains(text(), "Clearance"))]/text()').extract()

        sku = hxs.select('//div[@class="product-code"]/text()').re(r'Product code:(.*)')[0].strip()
        name = ' '.join(map(lambda x: x.strip(), hxs.select('//h1/span/text()').extract()))

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('name', name)
        loader.add_value('url', response.url)
        loader.add_value('brand', response.meta['brand'])
        loader.add_value('category', category)
        loader.add_value('sku', sku)
        loader.add_value('identifier', sku)
        image_url = hxs.select('//img[contains(@class, " featuredProductImage")]/@src').extract()
        if image_url:
            loader.add_value('image_url', image_url[0])

        availability = ''.join(re.findall('availabilityMessage = "(.*)";', response.body)).upper()
        if 'IN STOCK' not in availability and 'HURRY' not in availability:
            loader.add_value('stock', 0)

        price = data['currentPrice'] if data else ''
        if not price:
            price = hxs.select('//div[@id="productDetailsRefinementBlock"]/div/span/p[@class="priceNow"]/span[@class="value"]/text()').extract()
            if not price:
                price = hxs.select('//span[@id="productPriceContainer"]/p[@class="price"]/text()').extract()
            price = price[0] if price else 0

        loader.add_value('price', price)

        if loader.get_output_value('price') < 50:
            loader.add_value('shipping_cost', 3.50)

        yield loader.load_item()


