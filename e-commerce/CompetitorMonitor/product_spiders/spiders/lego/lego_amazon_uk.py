import csv
import os
import copy

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy.http.cookies import CookieJar

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from scrapy.utils.response import open_in_browser

HERE = os.path.abspath(os.path.dirname(__file__))

class AmazonSpider(BaseSpider):
    name = 'lego-amazon.co.uk'
    allowed_domains = ['amazon.co.uk']

    def start_requests(self):
        with open(os.path.join(HERE, 'products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                sku = row['sku']
                url = 'http://www.amazon.co.uk/s/ref=nb_sb_noss_1?' + \
                      'url=search-alias%%3Dtoys&field-keywords=lego+%s&x=0&y=0'

                yield Request(url % sku, meta={'sku': sku})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//div[@id="atfResults"]//div[starts-with(@id, "result_0")]')
        pr = None
        search_results = []
        for product in products:
            loader = ProductLoader(item=Product(), selector=product)
            name = product.select('.//*[contains(@class, "Title") or contains(@class, "title")]//a/text()').extract()
            if not name:
                name = product.select('h3[@class="newaps"]/a/span/text()').extract()
            loader.add_value('name', name)

            url = product.select('.//*[contains(@class, "Title") or contains(@class, "title")]//a/@href').extract()
            if not url:
                url = product.select('h3[@class="newaps"]/a/@href').extract()
            loader.add_value('url', url)

            price = product.select('.//*[@class="newPrice"]//span[contains(@class,"price")]/text()').extract()
            if not price:
                price = product.select('.//div[@class="usedNewPrice"]//span[@class="price"]/text()').extract()
            if not price:
                price = product.select('.//ul[@class="rsltGridList"]/li[1]/a/span[@class="bld lrg red"]//text()').extract()
            if not price:
                price = product.select('.//ul[@class="rsltGridList"]/li[1]/a/span[@class="price bld"]//text()').extract()
            if not price:
                price = product.select('.//ul[@class="rsltGridList grey"]/li[1]/a/span[@class="price bld"]//text()').extract()
            if not price:
                price = product.select('.//ul[@class="rsltGridList grey"]/li[1]/a/span[@class="bld lrg red"]//text()').extract()

            if price:
                loader.add_value('price', price[0].replace(',', '.'))
            loader.add_value('sku', response.meta['sku'])
            loader.add_value('identifier', response.meta['sku'])
            pr = loader
            search_results.append(pr)

        if search_results:
            cur_prod = search_results[0]
            next_prods = search_results[1:]
            yield Request(cur_prod.get_output_value('url'), callback=self.parse_product, meta={'cur_prod': cur_prod}, dont_filter=True)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        cur_prod = response.meta['cur_prod']
        product_desc = hxs.select('//div[@class="buying" and @style="padding-bottom: 0.75em;"]').extract()
        matched = False
        if product_desc:
            if "Dispatched from and sold by <b>Amazon.co.uk</b>" in product_desc[0].strip().replace('\n', ''):
                matched = True
        if not matched:
            cur_prod.add_value('name', ' - 3rd party')
        yield cur_prod.load_item()
