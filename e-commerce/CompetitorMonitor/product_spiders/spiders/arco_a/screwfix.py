import csv
import os
from decimal import Decimal

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter

from product_spiders.items import Product, \
    ProductLoaderWithNameStrip as ProductLoader

from product_spiders.base_spiders.primary_spider import PrimarySpider
from product_spiders.utils import extract_price


class ScrewfixSpider(PrimarySpider):
    name = 'arco-a-screwfix.com'
    allowed_domains = ['screwfix.com', 'competitormonitor.com']
    download_delay = 0.1

    csv_file = 'screwfix_products.csv'

    start_urls = ('http://www.screwfix.com',)

    def __init__(self, *args, **kwargs):
        super(ScrewfixSpider, self).__init__(*args, **kwargs)

        self.codes = {}

        with open(os.path.join(self.root_path, 'competitors_codes.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                identifier = row['url'].split(';')[0].split('/')[-1]
                self.codes[identifier] = row['code']


    def parse(self, response):
        url = "http://www.screwfix.com/jsp/account/ajax/switchIncExVat.jsp"
        
        yield Request(url, callback=self.parse_exc_vat) 

    def parse_exc_vat(self, response):
        yield Request('http://www.screwfix.com/', dont_filter=True, callback=self.parse_site) 

    def parse_site(self, response):

        cats = response.xpath('//div[@class="main-nav"]//a/@href').extract()
        for cat in cats:
            yield Request(urljoin_rfc(get_base_url(response), cat),
                          callback=self.parse_subcats)

    def parse_subcats(self, response):
        base_url = get_base_url(response)

        subcats = response.xpath('//div[@id="category_page_left_nav_container"]//a/@href').extract()

        #subcats.extend(response.xpath('//a[@forsubcatid]/@href').extract())
        #subcats.extend(response.xpath('//a[@class="page-link"]/@href').extract())

        for cat in subcats:
            yield Request(urljoin_rfc(get_base_url(response), cat),
                          callback=self.parse_subcats)

        next_page_url = response.xpath('//a[@id="next_page_link"]/@href').extract()
        if next_page_url:
            next_page_url = urljoin_rfc(base_url, next_page_url[0])
            next_page_url = add_or_replace_parameter(next_page_url, 'page_size', '100')
            yield Request(next_page_url, callback=self.parse_subcats)

        for product in self.parse_products(response):
            yield product

    def parse_products(self, response):
        products = response.xpath('//div[contains(@id, "product_box_")]')
        if not products:
            products = response.xpath('//div[@class="pad"]')

        category = response.xpath('//div[@id="breadcrumb_container_top"]//li/a[@class="bc__link bc__link--last"]/span/text()').extract()[0].strip()

        for product in products:
            product_url = product.select('.//a[starts-with(@id, "product_description")]/@href').extract()[0]
            details = product.select('.//p[starts-with(@id, "product_list_price")]/text()').extract()
            if details:
                if details[0].strip().startswith('From'):
                    yield Request(product_url, callback=self.parse_product)
                    continue

            price = product.xpath('.//h4[contains(@id, "product_list_price_")]/text()').extract()
            price = extract_price(price[0])

            loader = ProductLoader(selector=product, item=Product())
            loader.add_xpath('name', './/a[starts-with(@id, "product_description")]/@title')
            loader.add_value('url', product_url)
            loader.add_xpath('image_url', './/img[contains(@id, "product_image_")]/@src')
            loader.add_xpath('identifier', './/span/@quotenumberproductid')
            loader.add_value('sku', loader.get_output_value('identifier'))
            loader.add_value('price', price)
            loader.add_value('category', category)

            delivery = product.xpath('.//button[contains(@id, "product_add_button_") and contains(@title, "Delivery")]')
            collection = product.xpath('.//button[contains(@id, "add_for_collection_button_")]')
            if not delivery and not collection:
                loader.add_value('stock', 0)

            item = loader.load_item()

            no_items_variance = product.select('.//div[starts-with(@id, "product_list_price_container")]//div[@class="from"]').extract()
            if not no_items_variance:
                yield item
            else:
                yield Request(item['url'], callback=self.parse_product)

    def parse_product(self, response):
        """
        Parses individual product pages. Needed for simple run of BigSiteMethodSpider
        """

        categories = response.xpath('//div[contains(@class, "breadcrumb")]//li/a[@class="bc__link bc__link--last"]/span/text()').extract()
        if categories:
            category = categories[0].strip()

        price = ''.join(response.xpath('//div[@id="product_price"]//text()').extract()).strip()
        if not price:
            price = response.xpath('//span[@itemprop="price"]/text()').re(r'[\d.,]+')[0]

        price = extract_price(price)

        loader = ProductLoader(item=Product(), response=response)
        name = response.xpath('//span[@itemprop="name"]/text()').extract()[0].strip()
        loader.add_value('name', name)
        loader.add_xpath('identifier', '//span[@itemprop="productID"]/text()')
        loader.add_value('sku', loader.get_output_value('identifier'))
        loader.add_xpath('image_url', "//img[@itemprop='image']/@src")
        loader.add_value('url', response.url)
        loader.add_value('price', price)
        loader.add_value('category', category)

        delivery = response.xpath('.//button[contains(@id, "product_add_to_trolley") and contains(@title, "delivery")]')
        collection = response.xpath('.//button[contains(@id, "add_for_collection_button_")]')

        if not delivery and not collection:
            loader.add_value('stock', 0)

        yield loader.load_item()
