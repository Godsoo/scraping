import os
import csv
import json
import urlparse

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.spider import BaseSpider
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price

HERE = os.path.abspath(os.path.dirname(__file__))


class PCWorldSpider(BaseSpider):
    name = 'laptop_outlet-pcworld.co.uk'
    allowed_domains = ['pcworld.co.uk']
    start_urls = ['www.pcworld.co.uk']

    csv_file = os.path.join(HERE, 'laptop_outlet_results.csv')

    def start_requests(self):
        brands = []
        with open(self.csv_file) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['brand'].upper() not in brands:
                    brands.append(row['brand'].upper())

        search_url = "http://www.pcworld.co.uk/gbuk/search-keywords/xx_xx_xx_xx_xx/%s/xx-criteria.html"
        for brand in brands:
            yield Request(search_url % brand)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        # products
        products = hxs.select('//article//a[@class="in"]/@href').extract()
        products += hxs.select('//article//a[div[@class="in"]]/@href').extract()
        for product in products:
            yield Request(
                product.strip(),
                callback=self.parse_product
            )

        # products next page
        for next_page in set(hxs.select("//a[@class='next']/@href").extract()):
            yield Request(
                next_page.strip()
            )

        is_product = hxs.select('//meta[@property="og:type"]/@content').extract()

        if is_product:
            for product in self.parse_product(response):
                yield product


    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        url = response.url
        l = ProductLoader(item=Product(), response=response)

        # name
        name_l = hxs.select("//div[contains(@class,'product-page')]//h1[@class='page-title nosp']//text()").extract()
        name = ' '.join([x.strip() for x in name_l if x.strip()])
        l.add_value('name', name)

        # price
        price = hxs.select("//meta[@property='og:price:amount']/@content").extract()
        price = extract_price("".join(price))
        l.add_value('price', price)

        # sku
        sku = hxs.select("//div[contains(@class,'product-page')]//meta[@itemprop='identifier']/@content").extract()
        if sku:
            sku = sku[0].split(":")[-1]
            l.add_value('sku', sku)

        # identifier
        identifier = response.url.split('-')[-2]
        l.add_value('identifier', identifier)

        # category
        l.add_xpath('category', "//div[@class='breadcrumb']//a[position() > 1]/span/text()")

        # product image
        l.add_xpath('image_url', "//meta[@property='og:image']/@content")
        # url
        l.add_value('url', url)
        # brand
        json_data = response.xpath('//script[@type="application/ld+json"]/text()').extract()[-1].strip()
        try:
            data = json.loads(json_data)
            brand = data['brand']['name']
        except Exception:
            brand = ''
        l.add_value('brand', brand)
        # stock
        if hxs.select("//div[contains(concat('', @class,''), 'oos')]") \
                or hxs.select("//li[@class='unavailable']/i[@class='dcg-icon-delivery']"):
            l.add_value('stock', 0)
        else:
            l.add_value('stock', 1)

        product = l.load_item()

        yield product
