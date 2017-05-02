import os
import re
import xlrd
from product_spiders.items import Product
from product_spiders.base_spiders import PixmaniaBaseSpider
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy.selector import HtmlXPathSelector

from toymonitoritems import ToyMonitorMeta
from brands import BrandSelector


HERE = os.path.abspath(os.path.dirname(__file__))


class PixmaniaSpider(PixmaniaBaseSpider):
    name = 'toymonitor-pixmania.co.uk'
    allowed_domains = ['pixmania.co.uk']
    start_urls = ('http://www.pixmania.co.uk/')

    full_category_path = True
    collect_reviews = True

    reviews_url = 'http://api.bazaarvoice.com/data/batch.json?passkey=p3p838upc2ww2d1jyf02py2ai&apiversion=5.5&displaycode=16180-en_gb&resource.q0=reviews&filter.q0=isratingsonly%3Aeq%3Afalse&filter.q0=productid%3Aeq%3A22082447&filter.q0=contentlocale%3Aeq%3Aen_GB&sort.q0=relevancy%3Aa1&stats.q0=reviews&filteredstats.q0=reviews&include.q0=authors%2Cproducts%2Ccomments&filter_reviews.q0=contentlocale%3Aeq%3Aen_GB&filter_reviewcomments.q0=contentlocale%3Aeq%3Aen_GB&filter_comments.q0=contentlocale%3Aeq%3Aen_GB&limit.q0=30&offset.q0=0&limit_comments.q0=3&callback=bv_1111_23077'
    errors = []
    brand_selector = BrandSelector(errors)
    #field_modifiers = {'brand': brand_selector.get_brand}
    
    def start_requests(self):
        yield Request('http://www.pixmania.co.uk', callback=self.parse_toy_category)

    def parse_toy_category(self, response):
        categories = response.xpath('//li[.//h2[contains(strong/text(), "Toys")]]//li/a/@href').extract()
        for category in categories:
            yield Request(response.urljoin(category))

    def parse(self, response):
        base_url = get_base_url(response)

        filters = response.xpath('//nav[contains(@class, "ucmsNav")]//li/a/@href').extract()
        for url in filters:
            yield Request(urljoin_rfc(base_url, url))

        products = response.xpath('//form//div[contains(@class, "resultList")]/article'
                              '//*[contains(@class, "productTitle")]/a/@href').extract()

        for url in products:
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_product)

        pages = response.xpath('//ul[@class="pagination"]//a/@href').extract()

        for url in pages:
            yield Request(urljoin_rfc(base_url, url))

    def parse_product(self, response):
        sku = response.xpath('//input[@name="sFUPID"]/@value').extract()
        metadata = ToyMonitorMeta()
        ean = re.findall(u'data-flix-ean="(.*)"', response.body)
        if ean:
            metadata['ean'] = ean[0]
        promo = response.xpath('//div[@class="currentPrice"]/span[@class="block-reduc-red"]/text()').extract()
        if promo:
            metadata['promotions'] = promo[0]
        for obj in super(PixmaniaSpider, self).parse_product(response):
            if isinstance(obj, Product):
                obj['identifier'] = obj['identifier'].split('-')[0].strip()
                obj['sku'] = sku[0] if sku else obj['identifier']
                obj['metadata'] = metadata.copy()
            elif isinstance(obj, Request) and 'product' in obj.meta:
                obj.meta['product']['metadata'] = metadata.copy()
                obj.meta['product']['sku'] = sku[0] if sku else obj.meta['product']['identifier']
            yield obj
