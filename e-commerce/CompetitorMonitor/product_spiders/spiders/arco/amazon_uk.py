import csv
import os
import re
import urllib2
from decimal import Decimal

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from pricecheck import valid_price

HERE = os.path.abspath(os.path.dirname(__file__))

class AmazonSpider(BaseSpider):
    name = 'arco-amazon.co.uk'
    allowed_domains = ['amazon.co.uk']

    def start_requests(self):
        with open(os.path.join(HERE, 'arco_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = _filter_str(row['name'])
                sku = row['sku']
                description = _filter_str(row['full_description'])
                price = row['price']

                url = 'http://www.amazon.co.uk/s/ref=nb_sb_noss_1?url=search-alias%%3Daps&field-keywords=%s'
                name_req = Request(url % urllib2.quote(name), meta={'sku': sku})
                desc_req = Request(url % urllib2.quote(description))

                name_req.meta['sku'] = sku
                name_req.meta['desc_req'] = desc_req
                name_req.meta['price'] = price

                desc_req.meta['sku'] = sku
                desc_req.meta['name_req'] = name_req
                desc_req.meta['price'] = price

                yield name_req

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//div[@id="atfResults"]//div[starts-with(@id, "result_")]')
        # if not products:
            # products = hxs.select('//div[starts-with(@id, "result_")]')
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
                price = product.select('.//ul[@class="rsltL"]/li[1]/a/span[@class="bld lrg red"]//text()').extract()
            if not price:
                price = product.select('.//ul[@class="rsltL"]/li[1]/a/span[@class="price bld"]//text()').extract()
            if not price:
                price = product.select('.//ul[@class="rsltGridList grey"]/li[1]/a/span[@class="price bld"]//text()').extract()
            if not price:
                price = product.select('.//ul[@class="rsltGridList grey"]/li[1]/a/span[@class="bld lrg red"]//text()').extract()
            if not price:
                price = product.select('.//*[@class="newPrice"]//span/text()').extract()
            if not price:
                price = product.select('.//span[@class="bld lrg red"]//text()').extract()

            if price:
                if '-' in price[0]:
                    price = price[0].split('-')[0]
                else:
                    price = price[0]
                price = re.sub(u'[^\d\.,]', u'', price)
                price = Decimal(price.replace(',', '')) / Decimal(1.2)
                price = round(price, 2)
                loader.add_value('price', str(price))
            loader.add_value('sku', response.meta['sku'])
            loader.add_value('identifier', response.meta['sku'])
            pr = loader
            if price and valid_price(response.meta['price'], loader.get_output_value('price')):
                search_results.append(pr)

        if search_results:
            search_results.sort(key=lambda elem: elem.get_output_value('price'))
            cur_prod = search_results[0]
            next_prods = search_results[1:]
            meta = response.meta
            meta['cur_prod'] = cur_prod
            meta['next_prods'] = next_prods
            yield Request(cur_prod.get_output_value('url'), callback=self.parse_product, meta=meta, dont_filter=True)
        elif response.meta.get('desc_req'):
            yield response.meta.get('desc_req')

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        cur_prod = response.meta['cur_prod']
        product_desc = hxs.select('//div[@class="buying" and @style="padding-bottom: 0.75em;"]').extract()
        product = cur_prod.load_item()
        matched = False
        if product_desc:
            if "Dispatched from and sold by <b>Amazon.co.uk</b>" in product_desc[0].strip().replace('\n', ''):
                matched = True
        seller = hxs.select('//div[@class="buying" and @style="padding-bottom: 0.75em;"]/b/a/text()').extract()
        seller = seller[0].strip() if seller else u'---'
        name = product['name']
        if not matched:
            name += " 3rd party"
            # name = u'%s %s - %s' % (u'3rd', name, seller)
            product['name'] = name
        if 'arco' not in seller.lower():
            yield product
        else:
            next_prods = response.meta.get('next_prods', [])
            if next_prods:
                cur_prod = next_prods[0]
                next_prods = next_prods[1:]
                meta = response.meta
                meta['cur_prod'] = cur_prod
                meta['next_prods'] = next_prods
                yield Request(cur_prod.get_output_value('url'), callback=self.parse_product, meta=meta, dont_filter=True)
            elif response.meta.get('desc_req'):
                yield response.meta.get('desc_req')

def _filter_str(s):
    trim_strs = [
        "&trade;",
        "&reg;"
    ]
    res = s
    for trim_str in trim_strs:
        res = res.replace(trim_str, "")

    return res
