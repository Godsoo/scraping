import os
import csv

from decimal import Decimal

# from scrapy.spider import BaseSpider
from scrapy.contrib.spiders import SitemapSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class FeelUniqueSpider(SitemapSpider):
    name = 'cocopanda-feelunique.com'
    allowed_domains = ['feelunique.com']

    '''
    start_urls = ['http://www.feelunique.com/',
                  'http://www.feelunique.com/content/brands']
    '''

    sitemap_urls = ['http://www.feelunique.com/feelunique_products_sitemap.xml',
                    'http://www.feelunique.com/feelunique_brands_ranges_sitemap.xml']
    sitemap_rules = [
        ('/p/', 'parse_product'),
        ('/brands/', 'parse_categories')
    ]

    MAX_RETRY = 10

    def start_requests(self):
        for request in list(super(FeelUniqueSpider, self).start_requests()):
            yield request

        start_urls = ['http://www.feelunique.com/',
                      'http://www.feelunique.com/content/brands']

        for url in start_urls:
            yield Request(url)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        brand_urls = hxs.select('//div[@id="rightcolumn"]//a/@href').extract()

        categories = hxs.select('//*[@id="nav-container"]/ul/li/a/@href').extract()
        for category in categories:
            url = urljoin_rfc(get_base_url(response), category)
            yield Request(add_or_replace_parameter(url, 'curr', 'NOK'),
                          callback=self.parse_subcategories)

        for brand_url in brand_urls:
            yield Request(add_or_replace_parameter(urljoin_rfc(base_url, brand_url), 'curr', 'NOK'),
                          callback=self.parse_categories)

    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        category_urls = hxs.select('//div[@class="box-ranges"]//a/@href').extract()
        category_urls += (hxs.select('//*[@id="leftcolumn"]/ul[1]/li/a/@href').extract()
                          + hxs.select('//*[contains(@class, "content nav")]//a/@href').extract())
        for category_url in category_urls:
            yield Request(add_or_replace_parameter(urljoin_rfc(base_url, category_url), 'curr', 'NOK'),
                          callback=self.parse_products)

    def parse_subcategories(self, response):
        hxs = HtmlXPathSelector(response)
        sub_categories = hxs.select('//*[@id="leftcolumn"]/ul[1]/li/a') + hxs.select('//*[contains(@class, "content nav")]//a')
        for sub_category in set(sub_categories):
            url = urljoin_rfc(get_base_url(response), sub_category.select('@href').extract()[0])
            category = sub_category.select('span/text()').extract()
            if not category:
                category = sub_category.select('text()').extract()
            yield Request(url + '?curr=NOK',
                          callback=self.parse_brands,
                          meta={'category':category[0]})

    def parse_brands(self, response):
        hxs = HtmlXPathSelector(response)
        meta = response.meta
        brands = hxs.select('//div[@id="brand"]/div/ul/li/a')
        for brand in brands:
            meta['brand'] = brand.select('span/text()').extract()[0]
            url = urljoin_rfc(get_base_url(response), brand.select('@href').extract()[0])
            yield Request(url + '?curr=NOK',
                          callback=self.parse_products,
                          meta=meta)

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        meta = response.meta.copy()
        products = hxs.select('//div[@class="ProductPanel"]')
        if products:
            for product in products:
                loader = ProductLoader(item=Product(), selector=product)
                identifier = product.select('div[@class="options"]/a[@class="thickbox button pink"]/@href').extract()[0].split('p=')[-1]
                loader.add_xpath('name', 'h2/a/text()')
                loader.add_value('identifier', identifier)
                brand = meta.get('brand')
                if brand:
                    loader.add_value('brand', brand)
                else:
                    loader.add_xpath('brand', u'//div[@id="rightcolumn"]/h1/text()')
                category = meta.get('category')
                if category:
                    loader.add_value('category', category)
                else:
                    loader.add_xpath('category', u'//div[@id="breadcrumb"]//li/text()')
                loader.add_xpath('image_url', 'a[@class="thumb"]/img/@src')
                url = urljoin_rfc(get_base_url(response), ''.join(product.select('h2/a/@href').extract()))
                loader.add_value('url', url)
                price = ''.join(product.select('span[contains(@class, "price")]/text()').extract())
                if not price:
                    price = ''.join(product.select('div[@class="price"]/span[@class="new-price"]/text()').extract())
                if not price:
                    price = ''.join(product.select('span[contains(@class, "price")]//text()').extract())
                loader.add_value('price', price)
                yield loader.load_item()
            next = hxs.select('//a[@class="forward"]/@href').extract()
            if next:
                url = urljoin_rfc(get_base_url(response), next[0])
                yield Request(url, callback=self.parse_products)
        else:
            retry_times = meta['retry_times'] + 1 if 'retry_times' in meta else 0
            if retry_times < self.MAX_RETRY:
                self.log('ERROR - NO PRODUCTS FOUND, retrying... => %s' % response.url)
                meta['retry_times'] = retry_times
                yield Request(response.url, meta=meta, callback=self.parse_products, dont_filter=True)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        try:
            category = hxs.select('//div[@id="breadcrumb"]/ul/li/a/text()')[1].extract()
        except:
            category = ''

        price = ''.join(hxs.select('//span[contains(@class, "current-price")]//text()').extract())

        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('identifier', '//form[@id="buy-this-product"]/input[@name="p"]/@value')
        loader.add_xpath('name', '//div[@class="product-detail-information"]/h1/text()')
        loader.add_xpath('brand', '//div[@class="product-detail-information"]/a[@class="product-brand"]/img/@alt')
        loader.add_xpath('image_url', '//img[@class="main-image"]/@data-original-main')
        loader.add_value('url', response.url)
        loader.add_value('price', price)

        yield loader.load_item()
