# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.url import add_or_replace_parameter
import re
import json
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals
from scrapy.exceptions import DontCloseSpider

from product_spiders.spiders.pedalpedal.crcitem import CRCMeta


class PerformancebikeSpider(BaseSpider):
    name = u'performancebike.com'
    allowed_domains = ['www.performancebike.com']
    start_urls = [
        'http://www.performancebike.com/webapp/wcs/stores/servlet/AllBrandsView?catalogId=10551&langId=-1&categoryId=400345&storeId=10052'
    ]

    def _start_requests(self):
        yield Request('http://www.performancebike.com/bikes/Product_10052_10551_1104957_-1___400761', callback=self.parse_product)

    def __init__(self, *args, **kwargs):
        super(PerformancebikeSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.process_all_products, signals.spider_idle)
        self.get_brandless_products = 1

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        urls = hxs.select('//a[contains(@id,"WC_CachedCategoriesDisplay_Link_ForSubCat_")]/@href').extract()
        brands = hxs.select('//a[contains(@id,"WC_CachedCategoriesDisplay_Link_ForSubCat_")]/text()').extract()
        for url, brand in zip(urls, brands):
            url = add_or_replace_parameter(url, 'pageSize', '64')
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_product_list,
                          meta={'brand': brand})

    def process_all_products(self, spider):
        if spider.name == self.name and self.get_brandless_products:
            self.get_brandless_products = 0
            self.log("Spider idle. Processing all products")
            r = Request('http://www.performancebike.com/bikes/TopCategory_10052_10551_400278_-1_400278_Y',
                        callback=self.parse_categories)
            self._crawler.engine.crawl(r, self)
            raise DontCloseSpider

    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in hxs.select('//ul[@id="snVerticalMenu"]//h3/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url + '?pageSize=64'), callback=self.parse_product_list)
        for url in hxs.select('//span[@class="shopNow"]/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url + '&pageSize=64'), callback=self.parse_product_list)

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        brand = response.meta.get('brand', '')
        #products
        urls = hxs.select('//div[@class="product-info"]/h2/a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta={'brand': brand})
        #pagination
        page_start = int(response.meta.get('page_start', 0))
        page_start += 64
        if len(urls) == 64:
            url = add_or_replace_parameter(response.url, 'beginIndex', str(page_start))
            yield Request(url,
                          callback=self.parse_product_list,
                          meta={'page_start': page_start, 'brand': brand})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        if hxs.select('//p[contains(text(), "OOPS! Page not found.")]'):
            return

        product_name = hxs.select('//h1[@class="product_title"]/text()').extract()[0].strip()
        category = hxs.select('//ul[@class="pb-breadcrumb"]/li[2]/a/text()').extract()
        if category:
            category = category[0].strip()
            if category == 'Outlet Store':
                category = hxs.select('//ul[@class="pb-breadcrumb"]/li[3]/a/text()').extract()[0].strip()
        else:
            category = ''
        brand = response.meta.get('brand', '')
        image_url = hxs.select('//img[@id="image1"]/@src').extract()[0]
        image_url = image_url.rpartition('/')[0] + '/'
        sku = hxs.select('//span[@class="product_number"]/text()').extract()[0].strip().replace('#', '')
        price = hxs.select('//span[@class="sale_price_val"]/text()').extract()
        if not price:
            price = hxs.select('//span[@class="list_price_val"]/text()').extract()

        price = extract_price(price[0])

        rrp = ''.join(hxs.select('//span[contains(@class, "msrp_price_va")]/text()').extract())
        if not rrp:
            rrp = ''.join(hxs.select('//span[contains(@class, "list_price_val")]/text()').extract())
 
        rrp = extract_price(rrp)
        rrp = str(rrp) if rrp > price else ''

        product_config_reg = re.search(r'var productItems = (\[\s+\{.*\}\s+\])', response.body, re.DOTALL)
        if product_config_reg:
            json_string = product_config_reg.group(1)
            json_string = json_string.replace('\r', '').replace('\n', '').replace('\t', '').replace(' ', '')
            json_string = json_string.replace('},]', '}]').replace('\\', '\\\\')
            products = json.loads(json_string)
            for product in products:
                product_loader = ProductLoader(item=Product(), selector=hxs)
                identifier = product['itemId']
                product_loader.add_value('identifier', identifier)
                stock = product['inventoryNumber']
                if 'Avail.' in product['inVentoryMessage'] or 'OutofStock' in product['inVentoryMessage']:
                    stock = 0
                product_loader.add_value('stock', stock)
                image = product['mainImage']
                product_loader.add_value('image_url', urljoin_rfc(image_url, image))
                product_loader.add_value('url', response.url)
                product_loader.add_value('brand', brand)
                product_loader.add_value('sku', sku)
                product_loader.add_value('price', price)
                product_loader.add_value('category', category)
                color = product['color']
                name = product_name
                if color:
                    name += ', ' + color
                size = product['size']
                if len(size) > 0:
                    size = size[0]['longform']
                    name += ', {}'.format(size)
                product_loader.add_value('name', name)
                product = product_loader.load_item()
                metadata = CRCMeta()
                metadata['rrp'] = rrp
                product['metadata'] = metadata
                yield product
        else:
            self.log('WARNING!!! url: {}'.format(response.url))
