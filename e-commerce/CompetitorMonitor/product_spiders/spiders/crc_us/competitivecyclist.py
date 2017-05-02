# -*- coding: utf-8 -*-

"""
Name: competitivecyclist.com
Account: CRC US
"""


import re
import demjson
import json

from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc
from w3lib.url import url_query_cleaner

from product_spiders.spiders.pedalpedal.crcitem import CRCMeta


class CompetitivecyclistSpider(CrawlSpider):
    name = u'competitivecyclist.com'
    allowed_domains = ['competitivecyclist.com']
    start_urls = [
        'http://www.competitivecyclist.com/Store/sitemaps/categoriesIndex.jsp',
    ]
    
    rules = (
        Rule(LinkExtractor(allow='page=')),
        Rule(LinkExtractor(), callback='parse_category')
        )

    def parse_category(self, response):
        base_url = get_base_url(response)

        products = response.xpath('//div[@id="products"]//a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

        next_page = response.xpath('//li[@class="pag-next"]/a/@href').extract()
        if products:
            # This is to prevent some strange issues with website where it shows next page but there are no products
            for url in next_page:
                yield Request(urljoin_rfc(base_url, url), callback=self.parse_category)

    def parse_product(self, response):
        base_url = get_base_url(response)

        product_links = response.xpath('//div[@id="products"]//a[contains(@class,"qa-product-link")]/@href').extract()
        if product_links:
            for link in product_links:
                yield Request(url_query_cleaner(response.urljoin(link)), callback=self.parse_product)
            return

        product_name = response.xpath('//h1[@itemprop="name"]/text()').extract()
        if not product_name:
            return
        product_name = product_name[-1].strip()
        category = re.findall("name:'Category', value:'([^']+)'", response.body.replace("\\'", "&quote;"))
        if category:
            category = category.pop().replace("&quote;", "'")
        else:
            category = ""
        brand = response.xpath('//h1[@itemprop="name"]/span/text()').extract()
        brand = brand[0].strip() if brand else ''

        rrp_by_sku = {}

        sku_data = re.search(r'BC.product.skusCollection = \$.parseJSON\((.*)\);', response.body)
        if sku_data:
            sku_data = json.loads(demjson.decode(sku_data.group(1), encoding='utf8' ))
            rrp_by_sku = {sku.upper():str(opt['price']['high']) for sku, opt in sku_data.iteritems() if opt['price']['high']>opt['price']['low']}


        options = response.xpath('//li[contains(@class,"qa-variant-item-")]')
        for option in options:
            product_loader = ProductLoader(item=Product(), selector=option)
            sku = option.xpath('./@sku-value').extract()
            sku = sku[0]
            product_loader.add_value('sku', sku)
            product_loader.add_value('identifier', sku)
            option_name = option.xpath('./@title').extract()[0].strip()
            option_name = option_name.replace('One Color, One Size', '').replace(', One Size', '').replace('One Color, ', '').strip()
            if option_name != '':
                product_loader.add_value('name', product_name + ', ' + option_name)
            else:
                product_loader.add_value('name', product_name)
            image_url = option.xpath('./@data-img-large').extract()
            if image_url:
                product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            price = extract_price(option.xpath('./@data-price').extract()[0])
            product_loader.add_value('price', price)
            product_loader.add_value('url', response.url)
            product_loader.add_value('brand', brand)
            product_loader.add_value('category', category)
            product = product_loader.load_item()
            metadata = CRCMeta()
            metadata['rrp'] = rrp_by_sku.get(sku.upper(), '')
            product['metadata'] = metadata
            yield product
