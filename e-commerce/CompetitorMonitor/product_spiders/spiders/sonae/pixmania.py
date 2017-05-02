# -*- coding: utf-8 -*-

import os
import re
import csv

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from sonaeitems import SonaeMeta
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.config import DATA_DIR

HERE = os.path.abspath(os.path.dirname(__file__))


class PixmaniaSpider(BaseSpider):
    name = "sonae-pixmania.pt"
    allowed_domains = ["pixmania.pt"]
    start_urls = ["http://www.pixmania.pt"]
    categories = []
    skus = {}


    def start_requests(self):
        if hasattr(self, 'prev_crawl_id'):
            with open(os.path.join(DATA_DIR, '%s_products.csv' % self.prev_crawl_id)) as f:
                reader = csv.DictReader(f)
                skus = set()
                for row in reader:
                    if row['sku'] not in skus:
                        skus.add(row['sku'])
                        meta = {
                            'sku': row['sku'],
                        }
                        yield Request(row['url'], callback=self.parse_item, meta=meta)
        yield Request(self.start_urls[0], dont_filter=True)

    def parse(self, response):
        base_url = get_base_url(response)
        #skus = []
        #with open(os.path.join(HERE, 'items.csv')) as f:
            #reader = csv.reader(f)
            #for row in reader:
                #sku = row[0]
                #skus.append(sku)

        #sku = skus.pop()
        #yield Request('http://www.pixmania.pt/search/%s.html' % sku, meta={'dont_merge_cookies': True,
                                                                           #'skus': skus, 'sku': sku},
                      #callback=self.parse_search)

        hxs = HtmlXPathSelector(response)
        self.categories = hxs.select('//ul[@class="nav"]//a/@data-rel').extract()
        
        main_categories = hxs.select('//div[@class="category"]//a[@href]/@href').extract()
        for url in main_categories:
            self.log('Main category %s' %url)
            yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_results)
    
    def parse_main_category(self, response):
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//aside[@id="filters"]//nav[1]//a/@href').extract():
            yield Request(url, callback=self.parse_results)

    def parse_search(self, response):
        hxs = HtmlXPathSelector(response)

        products = hxs.select('//header[@class="productTitle"]/a/@href').extract()
        for p in products:
            self.log('SKU Match found: %s' % response.meta['sku'])
            self.skus[p] = response.meta['sku']

        skus = response.meta['skus']
        if skus:
            sku = skus.pop()
            yield Request('http://www.pixmania.pt/search/%s.html' % sku, meta={'skus': skus, 'sku': sku, 'dont_merge_cookies': True,},
                          callback=self.parse_search)
        else:
            for c in self.categories:
                yield Request(c, callback=self.parse_category)

            yield Request('http://www.pixmania.pt/sitemap-8-sp.html', callback=self.parse_sitemap,
                          meta={'dont_merge_cookies': True})

    def parse_category(self, response):
        categories = re.findall('href="([^"]*)"', response.body.replace('\\', ''))
        for c in categories:
            yield Request(urljoin_rfc(get_base_url(response), c), callback=self.parse_results, meta={'dont_merge_cookies': True})

    def parse_sitemap(self, response):
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//ul[@class="customList"]/li/a/@href').extract()
        for c in categories:
            yield Request(urljoin_rfc(get_base_url(response), c), callback=self.parse_results, meta={'dont_merge_cookies': True})

    def parse_results(self, response):

        hxs = HtmlXPathSelector(response=response)

        items = hxs.select("//header[@class='productTitle']//a/@href").extract()
        if not items:
            retry = response.meta.get('retry', 0)
            if retry < 3:
                yield Request(response.url, meta={'retry': retry + 1, 'dont_merge_cookies': True}, dont_filter=True)
            else:
                categories = hxs.select('//p[@class="header" and starts-with(text(), "Categoria")]/..//a/@href').extract()
                self.log('Subcategories')
                for c in categories:
                    yield Request(c, callback=self.parse_results, meta={'dont_merge_cookies': True})

        for item in items:
            url = item.split('/')
            all_dealers_url = url[:-1] + ['all_seller'] + url[-1:]
            all_dealers_url =  '/'.join(all_dealers_url)
            all_dealers_url = urljoin_rfc(get_base_url(response), all_dealers_url)
            url = '/'.join(url)
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_sku, meta={'url': item, 'dont_merge_cookies': True, 'all_dealers_urls': all_dealers_url})


        try:
            next_page = hxs.select("//a[@class='next']/@href").extract()[0]
            yield Request(next_page, callback=self.parse_results, meta={'dont_merge_cookies': True})
        except:
            pass

    def parse_sku(self, response):
        if response.url.endswith("/index.html"):
            return

        response = response.replace(body=response.body.decode('utf-8', errors='ignore'))

        meta = response.meta
        sku = None

        ean = re.search('data-flix-ean="(.*)"', response.body)
        if ean:
            sku = ean.group(1)
        else:
            pn = re.search("pn', '(.*)']", response.body)
            if pn:
                sku = pn.group(1)
        meta['sku'] = sku

        yield Request(meta['all_dealers_urls'], callback=self.parse_item, meta=meta)

    def parse_item(self, response):
        if response.url.endswith("/index.html"):
            return

        response = response.replace(body=response.body.decode('utf-8', errors='ignore'))

        hxs = HtmlXPathSelector(response=response)

        description_field = hxs.select('''//script[contains(text(), '"prdref"')]''').extract()
        description_field = description_field[0] if description_field else ''

        try:
            name = re.findall(re.compile('\"prdname\"\,\"(.+?)\"'),        description_field)[0]
        except:
            name = hxs.select("//span[@itemprop = 'name']/text()").extract()[0]

        sku = response.meta.get('sku', None)
        if not sku:
            url_orig = response.meta['url']
            if url_orig in self.skus:
                sku = self.skus[url_orig]
            else:
                sku = re.findall(re.compile('\"prdref\"\,\"(.+?)\"'),         description_field)[0]

        brand = re.findall(re.compile('\"prdparam-brand\"\,\"(.+?)\"'), description_field)

        identifier = hxs.select("//input[@name = 'sProductId']/@value").extract()[0]

        categories = hxs.select('//div[@class="breadcrumb"]//span[@itemprop="title"]/text()').extract()
        categories = [c for c in categories if c.strip() and c.strip().lower() != 'home'][:3]

        try:
            image_url = hxs.select("//article[@class='product cancelOverfProduct col9']//img/@src").extract()[0]
        except:
            image_url = ""

        dealers = hxs.select('//div[@class="merchant product"]')
        for dealer in dealers:
            l = ProductLoader(item=Product(), response=response)
            stock = dealer.select('.//span[@class="available"]')
            price = dealer.select('.//span[@class="currentPrice"]//text()').extract()
            price = ''.join(price).replace(',', '.')
            shipping = dealer.select('.//div[@class="productPrices"]/span/text()').extract()
            shipping = ''.join(shipping[-1]).replace(',', '.') if shipping else '0'


            seller = dealer.select('.//p[@class="soldby"]/strong/a//text()').extract()

            if not seller:
                seller = ['Pixmania']

            if 'Pixmania' in seller:
                continue

            prod_id = identifier + '-' + seller[0].lower()
            l.add_value('image_url', image_url)
            l.add_value('url', response.url)
            l.add_value('name', name)
            l.add_value('price', price)
            if not stock:
                l.add_value('stock', 0)
            l.add_value('category', categories)
            if brand:
                l.add_value('brand', brand[0])
            l.add_value('shipping_cost', shipping)
            l.add_value('identifier', prod_id)
            l.add_value('dealer', seller)
            l.add_value('sku', sku)

            product = l.load_item()

            metadata = SonaeMeta()
            metadata['exclusive_online'] = 'Yes'
            delivery = dealer.re(r'Expedido dentro de (\d+)')
            if delivery:
                delivery_days = int(delivery[0])
                if delivery_days == 1:
                    metadata['delivery_24'] = 'Yes'
                elif delivery_days == 2:
                    metadata['delivery_24_48'] = 'Yes'
                elif delivery_days < 5:
                    metadata['delivery_48_96'] = 'Yes'
                elif delivery_days >= 5:
                    metadata['delivery_96_more'] = 'Yes'
            previous_price = dealer.select('.//span[@class="previousPrice"]/del/text()').re(r'[\d,.]+')
            if previous_price:
                metadata['promotion_price'] = previous_price[0].replace('.', '').replace(',', '.')
            product['metadata'] = metadata
            yield product
