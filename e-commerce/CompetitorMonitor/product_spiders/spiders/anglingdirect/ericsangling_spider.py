import re

# from scrapy.spider import BaseSpider
from product_spiders.base_spiders.primary_spider import PrimarySpider

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price

from scrapy.http import FormRequest
import os
import csv

'''
PrimarySpider is used to copy the data and then use it as cache at the next crawl.
This allow us does not parse the product page again.
'''
class ericsangling_spider(PrimarySpider):
    name = 'ericsangling.co.uk'
    allowed_domains = ['ericsangling.co.uk', 'www.ericsangling.co.uk', 'www.britnett-carveradv.co.uk', 'britnett-carveradv.co.uk']
    start_urls = ('http://www.ericsangling.co.uk/index.php/special-offers.html',)

    csv_file = 'ericsangling_co_uk_crawl.csv'

    def __init__(self, *args, **kwargs):
        super(ericsangling_spider, self).__init__(*args, **kwargs)

        self.previous_crawl_data = {}

        # It supposed that self.crawl_results_file_path has been set in PrimarySpider.__init__ method
        if os.path.exists(self.crawl_results_file_path):
            with open(self.crawl_results_file_path) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.previous_crawl_data[row['identifier']] = row

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        category_urls = response.xpath('//ul[@id="sidebar-nav-menu"]//a/@href').extract()
        for url in category_urls:
            yield Request(urljoin_rfc(base_url, url), dont_filter=True, callback=self.parse_sub)

    def parse_sub(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        items = hxs.select('//ol[@id="products-list"]/li')
        for item in items:
            product_id = item.select('.//span[contains(@id, "product-price-")]/@id').re(r'product-price-(\d+)')
            product_id = product_id[0] if product_id else ''
            if product_id and product_id in self.previous_crawl_data:
                self.log('>>> CACHED PRODUCT => %s' % product_id)
                loader = ProductLoader(item=Product(**self.previous_crawl_data[product_id]), selector=item)
                loader.replace_xpath('price', './/span[@id="product-price-%s"]//text()' % product_id, re=r'([\d.,]+)')
                if item.select('.//p[@class="availability out-of-stock"]'):
                    loader.replace_value('stock', 0)
                yield loader.load_item()
            else:
                product_url = item.select('.//h2[@class="product-name"]/a/@href').extract()
                if product_url:
                    yield Request(urljoin_rfc(base_url, product_url[0]), callback=self.parse_product)

        for url in set(hxs.select('//div[@class="pages"]//a/@href').extract()):
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_sub)


    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        breadcrumbs_cats = hxs.select('//div[@class="breadcrumbs"]//li[contains(@class, "category")]/a/text()').extract()
        if breadcrumbs_cats:
            category = breadcrumbs_cats[-1]
        else:
            category = ''

        image_url = hxs.select('//img[@id="image-main"]/@src').extract()
        image_url = image_url[0] if image_url else ''

        many_items = hxs.select('//table[@id="super-product-table" and contains(@class, "grouped-items-table")]//tr')[1:]
        if many_items:
            for item in many_items:
                try:
                    product_id = item.select('.//input[@class="input-text qty"]/@name').re(r'(\d+)')[0]
                except:
                    continue

                loader = ProductLoader(item=Product(), selector=item)
                loader.add_value('url', urljoin_rfc(base_url, response.url))
                loader.add_xpath('name', 'td[1]/text()')
                price = item.select('.//p[@class="special-price"]/span[@class="price"]//text()').extract()
                if not price:
                    price = item.select('.//span[@class="regular-price"]/span[@class="price"]//text()').extract()
                price = price[0].strip() if price else '0'
                loader.add_value('price', price)
                loader.add_value('category', category)
                loader.add_value('image_url', image_url)
                loader.add_value('identifier', product_id)
                stock = item.select('.//td[position()=last()]/text()').re('(\d+)')
                if stock and int(stock[0]) == 0:
                    loader.add_value('stock', 0)

                yield loader.load_item()
        else:
            product_id = response.xpath('//input[@name="product"]/@value').extract()[0]

            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('url', urljoin_rfc(base_url, response.url))
            loader.add_xpath('name', '//div[@class="product-name"]/h1/text()')
            price = response.xpath('//p[@class="special-price"]/span[@class="price"]/text()').extract()
            if not price:
                price = response.xpath('//span[@class="regular-price"]/span/text()').extract()
            loader.add_value('price', price)
            loader.add_value('category', category)
            loader.add_value('image_url', image_url)
            stock = response.xpath('//p[@class="availability in-stock"]')
            if not stock:
                loader.add_value('stock', 0)
            loader.add_value('identifier', product_id)

            yield loader.load_item()

