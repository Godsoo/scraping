# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from urlparse import urljoin as urljoin_rfc
from product_spiders.utils import extract_price
from scrapy.item import Item, Field

import re

class CRCMeta(Item):
    rrp = Field()

class CyclingexpressSpider(BaseSpider):
    name = u'crc_au-cyclingexpress.com'
    allowed_domains = ['www.cyclingexpress.com']
    download_delay = 2
    brands = []

    def start_requests(self):
        url = 'http://www.cyclingexpress.com/include/Ajax/ajax.base.php?action=web_base_setting&web_lang=en&web_currency=AUD&web_destination=AUS&web_url='
        yield Request(url, method='POST')

    def parse(self, response):
        yield Request('http://www.cyclingexpress.com/en/brandindex.html', callback=self.parse_links)

    def parse_links(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        for brand in hxs.select('//li[a[contains(@href, "brand")]]/p/text()').extract():
            self.brands.append(brand.strip())
        for url in hxs.select('//*[@id="nav"]//div[@class="downmenu"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list)

    def parse_products_list(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//nav[@class="pageLink"]/a/text()').extract()
        cats = []
        for category in categories:
            if category != 'Products':
                cats.append(category)
        products = hxs.select('//div[@class="productFrame"]/a/@href').extract()
        pages = hxs.select('//ul[@class="pageBar"]/li/a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta={'categories': cats})
        for url in pages:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list)

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        name = hxs.select('//*[@id="Pbox"]/nav[1]/a[3]/text()').extract()[0]
        brand = ''
        for b in self.brands:
            if name.upper().startswith(b.upper()):
                brand = b
                break
        identifier = re.findall('roduct.ia\/(\d+)\/', response.url)[0]
        image_url = hxs.select('//*[@id="thumbnail"]//li/a/@href').extract()
        image_url = urljoin_rfc(base_url, image_url[0]) if image_url else ''
        category = response.meta.get('categories')
        products = hxs.select('//*[@id="priceBox"]/form/table/tr[position()>1]')
        for product in products:
            item = Product()
            list_price = extract_price(product.select('./td[2]/span[@class="tGrey"]/text()').extract()[0])
            metadata = CRCMeta()
            metadata['rrp'] = list_price
            item['metadata'] = metadata

            loader = ProductLoader(item=item, selector=product)
            option_name = product.select('./td/b[@class="name"]/text()').extract()[0]
            loader.add_value('name', name + ', ' + option_name)
            loader.add_value('brand', brand)
            loader.add_value('url', response.url)
            loader.add_value('category', category)
            loader.add_value('image_url', image_url)
            option_id = product.select('./td/div/button/@onclick').extract()[0]
            if 'proEmailMe' in option_id:
                option_id = option_id.split('proEmailMe(')[1].split(')')[0].replace("'", '').split(',')
            else:
                option_id = option_id.split('shopCartAdd(')[1].split(')')[0].replace("'", '').split(',')
            option_id = option_id[0].strip() + '_' + option_id[1].strip()
            loader.add_value('identifier', identifier + '_' + option_id)
            price = product.select('./td[2]/b/text()').extract()
            price = extract_price(price[0])
            loader.add_value('price', price)
            sku = product.select('./td[1]/div/text()').extract()
            sku = sku[0] if sku else ''
            loader.add_value('sku', sku)
            stock = product.select('./td[1]/span[@class="tGrey"]/text()').extract()[0]
            if stock != 'In Stock':
                loader.add_value('stock', 0)
            yield loader.load_item()
