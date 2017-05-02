import csv
import os

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from pricecheck import valid_price

HERE = os.path.abspath(os.path.dirname(__file__))

class AmazonSpider(BaseSpider):
    name = 'bricoman-amazon.it'
    allowed_domains = ['amazon.it']

    def start_requests(self):
        with open(os.path.join(HERE, 'bricoman_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                sku = row['bricoman_code']
                url = 'http://www.amazon.it/s/ref=nb_sb_noss?__mk_it_IT=%%C3%%85M%%C3%%85Z%%C3%%95%%C3%%91&url=search-alias%%3Daps&field-keywords=%s'

                yield Request(url % row['model'].replace(' ', '+'), meta={'sku': sku, 'price': row['price']})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//div[@id="atfResults"]//div[starts-with(@id, "result_")]')
        products += hxs.select('//div[@id="btfResults"]//div[starts-with(@id, "result_")]')
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
                price = product.select('.//div[@class="usedPrice"]//span//text()').extract()
            if not price:
                price = product.select('.//ul[@class="rsltGridList"]/li[1]/a/span[@class="bld lrg red"]//text()').extract()
            if not price:
                price = product.select('.//ul[@class="rsltGridList grey"]/li[1]/a/span[@class="price bld"]//text()').extract()
            if not price:
                price = product.select('.//ul[@class="rsltGridList grey"]/li[1]/a/span[@class="bld lrg red"]//text()').extract()
            if not price:
                price = product.select('.//ul[@class="rsltL"]/li[1]/a/span[@class="bld lrg red"]//text()').extract()
            if not price:
                price = product.select('.//ul[@class="rsltL"]/li[1]/a/span[@class="price bld"]//text()').extract()
            if not price:
                price = product.select('.//ul[@class="rsltL"]/li[1]/a/span[@class="bld lrg red"]//text()').extract()
            print price

            if price:
                loader.add_value('price', price[0].replace(',', '.'))
            else:
                self.log("No price found")
                continue
            loader.add_value('sku', response.meta['sku'])
            loader.add_value('identifier', response.meta['sku'])
            pr = loader
            if valid_price(response.meta['price'], pr.get_output_value('price')):
                search_results.append(pr)

        search_results.sort(key=lambda x: x.get_output_value('price'))

        if search_results:
            cur_prod = search_results[0]
            next_prods = search_results[1:]
            yield cur_prod.load_item()
