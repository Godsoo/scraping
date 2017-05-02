import re
import json

from datetime import datetime
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request

from scrapy.item import Item, Field
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from decimal import Decimal
from product_spiders.items import (Product, ProductLoaderWithNameStrip as ProductLoader)
from scrapy.contrib.loader.processor import MapCompose, Join, TakeFirst, Identity
from scrapy.contrib.loader import XPathItemLoader
from scrapy.utils.markup import remove_entities
from product_spiders.utils import extract_price
import logging
import urlparse


from demoritems import DemoRMeta, Review, ReviewLoader


class ArgosCoUKKeterSpider(BaseSpider):
    name = 'demo_r-argos.co.uk'
    allowed_domains = ['argos.co.uk', 'argos.ugc.bazaarvoice.com', 'argos.scene7.com']
    start_urls = ['https://argosresearchstorage.blob.core.windows.net/meganav/navigation.json']

    extract_reviews = False

    def parse(self, response):

        data = json.loads(response.body)
        for column in data[0]['columns']:
            column_title = column['sections'][0]['title']
            if column_title == "Sound & Vision" or column_title == "Computing & Phones":
                for url in column['sections'][0]['links']:
                    yield Request(url['link'], callback=self.parse_categories)

    def parse_categories(self, response):

        sub_categories = response.xpath('//ul[@id="categoryList"]//a/@href').extract()
        for url in sub_categories:
            yield Request(response.urljoin(url), callback=self.parse_categories)

        pages = response.xpath('//a[@class="page"]/@href').extract()
        for url in pages:
            yield Request(response.urljoin(url), callback=self.parse_categories)

        products = response.xpath('//a[@id="optimiseProductURL"]/@href').extract()
        for url in products:
            yield Request(response.urljoin(url), callback=self.parse_product,
                    meta={'category': ' > '.join([x.split('|')[2].replace('+', ' ') for x in response.xpath('//form[@id="refineform"]//input[starts-with(@name,"c_")]/@value').extract()])})

    def parse_product(self, response):
        url = response.url

        options = response.xpath('//a[contains(@id, "pickerItem")]/@href').extract()
        for option in options:
            option_url = urlparse.urljoin(get_base_url(response), option)
            yield Request(option, callback=self.parse_product)

        l = ProductLoader(item=Product(), response=response)

        name = response.xpath('//h1[@class="product-name-main"]/*[@itemprop="name"]/text()').extract()
        name = name[0].strip()
        l.add_value('name', name)

        price = response.xpath('//div[contains(@class, "product-price-wrap")]/div[@itemprop="price"]/@content').extract()
        price = extract_price("".join(price).strip())
        l.add_value('price', price)

        sku = response.xpath("//p//text()[contains(., 'EAN')]").re('EAN: (.*)\.')
        if sku:
            sku = sku[0].split(":")[-1].split('.')[0].strip()
            l.add_value('sku', sku)

        identifier = response.url.split('/')[-1].split('.')[0]
        l.add_value('identifier', identifier)

        categories = response.xpath('//ol[contains(@class, "breadcrumb")]//a/span/text()').extract()[-3]
        """
        if categories:
            categories = categories[0].split('|')

        if not categories:
            categories = re.findall('s.eVar3="(.*)"', response.body)
            if categories:
                categories = categories[0].split('>')
        """
        l.add_value('category', categories)

        l.add_value('category', categories)
        image_url = response.xpath('//meta[@property="og:image"]/@content').extract()
        l.add_value('image_url', image_url)
        l.add_value('url', url)
        l.add_xpath('brand', "//span[@class='product-name-brand']/a[@itemprop='brand']/text()")
        product = l.load_item()

        metadata = DemoRMeta()
        metadata['promotion'] = ''.join(response.xpath('//div/span[@class="price-was"]/text()').extract())
        metadata['reviews'] = []
        product['metadata'] = metadata

        if not product.get('image_url', None):
            image_url_req = 'http://argos.scene7.com/is/image/Argos?req=set,json&imageSet='+product['identifier']+'_R_SET'
            yield Request(image_url_req, callback=self.parse_image, meta={'product': product})
        else:
            yield product

    def parse_image(self, response):
        product = response.meta['product']
        image_url = re.findall('"img_set","n":"(.*)","item', response.body)
        if image_url:
            image_url = 'http://argos.scene7.com/is/image/' + image_url[0]
            product['image_url'] = image_url

        yield product
