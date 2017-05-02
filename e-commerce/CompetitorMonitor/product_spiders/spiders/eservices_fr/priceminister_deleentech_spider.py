# -*- coding: utf-8 -*-
import os
import re
import csv
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader, ProductLoaderEU
from product_spiders.utils import extract_price_eu as extract_price
from product_spiders.config import DATA_DIR

from eservicesfritems import EservicesFrMeta


class PriceministerDeleentechSpider(BaseSpider):
    name = 'eservicesgroup-fr-priceminister-deleentech'
    allowed_domains = ['priceminister.com']
    start_urls = ['http://www.priceminister.com/boutique/DeleenTech/nav']

    products_url = 'http://www.priceminister.com/offer?action=desc&aid=%(aid)s&productid=%(productid)s'
    pages_url = 'http://www.priceminister.com/boutique/DeleenTech/pa/%(pa)s/nav'

    rotate_agent = True
    
    def start_requests(self):
        if hasattr(self, 'prev_crawl_id'):
            with open(os.path.join(DATA_DIR, '%s_products.csv' % self.prev_crawl_id)) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    yield Request(row['url'], callback=self.parse_product)
        if hasattr(self, 'missing_urls') and isinstance(self.missing_urls, list):
            for url in self.missing_urls:
                yield Request(url, callback=self.parse_product)
        yield Request(self.start_urls[0])

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products_data = hxs.select('//div[@class="mf_hproduct"]//h3/span/@data-pmbt').extract()
        products_data += hxs.select('//div[@class="mf_hproduct"]//h3/a/@data-pmbt').extract()
        for pdata in products_data:
            dta = pdata.split(',')
            yield Request(self.products_url % {'aid': dta[9][1:-1], 'productid': dta[13][1:-1]}, callback=self.parse_product)

        pages = hxs.select('//li[@class="page_num"]/a/text()').extract()
        for pa in pages:
            yield Request(self.pages_url % {'pa': pa})


    def parse_product(self, response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        loader = ProductLoader(item=Product(), response=response)

        price = ''.join(hxs.select('//li[contains(@class, "price")]/text()').extract())
        price = ''.join(re.findall('([\d\.,]+)', price))
        if not price:
            price = ''.join(hxs.select("//span[contains(@class,'price')]/text()").extract())
        name = filter(lambda s: s.strip(), hxs.select('//div[@class="fn"]/h1//text()').extract())
        stock = 1 if 'data_layer[\'summary_available_stock\'] = "true";' in response.body else 0
        categories = hxs.select('//div[@id="location"]//text()').extract()[:-1]
        image_url = hxs.select('//img[@class="photo"]/@src').extract()
        image_url = image_url[0] if image_url else ''
        identifier = re.findall('productid=(\d+)', response.url)
        if not identifier:
            identifier = re.findall('pid=(\d+)', hxs.select('//meta[@property="og:url"]/@content').extract()[0])
            if not identifier:
                identifier = re.findall('\/buy\/(\d*)', response.url)
        identifier = identifier[0] if identifier else ''
        sku = re.findall(u'summary_product_id\'] = "(.*)";', response.body)
        sku = sku[0] if sku else identifier

        loader.add_value('url', response.url)
        loader.add_value('sku', sku)
        loader.add_value('identifier', identifier)

        for category in categories:
            if '>' not in category:
                loader.add_value('category', category)

        if not price:
            cid = re.findall("\"cid\": (\d*)", response.body)[0]
            url_name = re.findall("urlname=(.+?)&", response.body)[0]
            url = 'http://www.priceminister.com/mfp?action=advlstmeta&cid={}&urlname={}&htp=false&hpbs=false&isExternalRefererMFP=true&pid={}&ifl=false'.format(cid, url_name, identifier)
            yield Request(url, meta={'loader': loader}, callback=self.parse_price)
        else:
            price = extract_price(price)
            loader.add_value('price', price)
            loader.add_value('image_url', image_url)
            loader.add_value('stock', stock)
            loader.add_value('name', name)
            loader.add_xpath('brand', '//span[@class="hbis"]//text()')

            item = loader.load_item()
            metadata = EservicesFrMeta()
            mpn = hxs.select('//li[span[contains(text(), "rence fabricant")]]/em/text()').extract()
            metadata['mpn'] = mpn[0] if mpn else ''
            item['metadata'] = metadata

            yield item


    def parse_price(self, response):

        hxs = HtmlXPathSelector(response)
        loader = response.meta['loader']

        price = hxs.select("//span[@class='price_origin']//span[@class='value']/text()").extract()
        if not price:
            price = hxs.select("//div[@id='buybox']//li[contains(@class,'price')]/text()").extract()
        price = extract_price(price[0])
        image_url = hxs.select('//img[@itemprop="image"]/@src').extract()
        image_url = image_url[0] if image_url else ''
        name = hxs.select("//h1[@itemprop='name']/text()").extract()[0]
        brand = hxs.select("//span[@class='hbis']/a/text()").extract()[0]
        stock = 1 if hxs.select("//*[contains(text(),'Ajouter')]").extract() else 0

        loader.add_value("price", price)
        loader.add_value("name", name)
        loader.add_value("image_url", image_url)
        loader.add_value("brand", brand)
        loader.add_value("stock", stock)

        yield loader.load_item()
