# -*- coding: utf-8 -*-
import os
import csv
import json

from w3lib.url import add_or_replace_parameter
from scrapy.spider import BaseSpider
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from sonaeitems import SonaeMeta
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from product_spiders.config import DATA_DIR

import shutil

from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals

HERE = os.path.abspath(os.path.dirname(__file__))


class WortenSpider(BaseSpider):
    name = "sonae-worten.pt"
    allowed_domains = ["worten.pt"]
    # search_url = 'https://www.worten.pt/search?sortBy=relevance&hitsPerPage={}&page={}&query=*'
    sitemap_url = 'https://www.worten.pt/diretorio-de-categorias'
    per_page = 48
    products = {}
    custom_settings = {'COOKIES_ENABLED': True}

    def __init__(self, *args, **kwargs):
        super(WortenSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_closed, signals.spider_closed)

    def spider_closed(self, spider):
        if spider.name == self.name:
            shutil.copy('data/worten_products.csv', os.path.join(HERE, 'fnac_products.csv'))

    def start_requests(self):
        filename = None
        if hasattr(self, 'prev_crawl_id'):
            filename = os.path.join(DATA_DIR, '%s_products.csv' % self.prev_crawl_id)

        if filename is not None and os.path.exists(filename):
            with open(filename) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.products[row['identifier'].decode('utf8')] = row['category'].decode('utf8')

        self.log('{} products loaded from cache'.format(len(self.products)))

        yield Request(self.sitemap_url, meta={'dont_merge_cookies': True}, cookies={}, callback=self.parse_site_map)

        # yield Request(self.search_url.format(self.per_page, 1), callback=self.parse_total,
        #               meta={'dont_merge_cookies': True}, cookies={})

    def parse_total(self, response):
        total = response.css('.search-list').css('.w-filters__results').xpath('text()').extract_first().split('de ')[1]
        for x in range(1, int(total) / self.per_page + 1):
            yield Request(self.search_url.format(self.per_page, x), meta={'dont_merge_cookies': True},
                          dont_filter=True, cookies={}, callback=self.parse_list)

    def parse_site_map(self, response):
        cats = response.xpath("//ul/li/ul/li/ol/li/a/@href").extract()
        for url in set(cats):
            if not url or url == '#':
                continue
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_list,
                          meta={'dont_merge_cookies': True},
                          cookies={})

    def parse_list(self, response):
        products = response.css('.w-product[itemscope]')
        for product in products:
            url = product.xpath(".//a[@itemprop='url']/@href").extract_first()
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product,
                          meta={'dont_merge_cookies': True},
                          cookies={})
        
        pages = response.css('ul.pagination a::attr(data-page)').extract()
        for page in pages:
            url = add_or_replace_parameter(response.url, 'page', page)
            yield Request(url, callback=self.parse_list,
                          meta={'dont_merge_cookies': True},
                          cookies={})
            
    def parse_product(self, response):
        description_field = response.xpath("//script[contains(text(), 'var dataLayer')]/text()").re('dataLayer = \[(.*)\];')[0]
        description_field = json.loads(description_field)

        name = description_field['productName']
        price = description_field['productPrice']
        brand = description_field['productBrand']
        categories = response.css('.breadcrumbs').xpath('li/a/text()').extract()
        ean = response.css('.w-product-details').xpath(".//li[span[contains(text(), 'EAN')]]/span[@class='details-value']").xpath('text()').extract_first()
        image_url = response.xpath("//img[@id='product-main-image']/@src").extract_first()
        identifier = description_field['productId']

        ref_code = description_field['productSKU']

        two_four_days = bool(response.css('.w-product__availability').xpath('.//p[contains(text(), "2 a 4")]'))

        l = ProductLoader(item=Product(), response=response)
        
        if image_url:
            l.add_value('image_url', response.urljoin(image_url))
        l.add_value('url', response.url)
        l.add_value('name', name)
        l.add_value('price', price)
        l.add_value('brand', brand)

        l.add_value('sku', ean)
        l.add_value('identifier', identifier)
        if identifier in self.products:
            categories = self.products.get(identifier, '').split(' > ')
        for category in categories:
            l.add_value('category', category.strip())
        product = l.load_item()

        product['metadata'] = SonaeMeta()
        product['metadata']['exclusive_online'] = 'No'
        if two_four_days:
            product['metadata']['delivery_48_96'] = 'Yes'
        else:
            product['metadata']['delivery_96_more'] = 'Yes'

        if ref_code:
            product['metadata']['ref_code'] = ref_code

        yield product
