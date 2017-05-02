# -*- coding: utf-8 -*-
from urlparse import urljoin as urljoin_rfc

from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector
from scrapy.spider import BaseSpider
from scrapy.utils.response import get_base_url
from scrapy.utils.url import add_or_replace_parameter

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price

from product_spiders.base_spiders.primary_spider import PrimarySpider


class JunoCoUkSpider(PrimarySpider):
    name = u'studioxchange-juno.co.uk'
    allowed_domains = ['www.juno.co.uk']
    start_urls = [
        'http://www.juno.co.uk/dj-equipment/?items_per_page=500&show_out_of_stock=1&currency=GBP',
        'http://www.juno.co.uk/studio-equipment/?items_per_page=500&show_out_of_stock=1&currency=GBP']
    errors = []

    csv_file = 'juno.co.uk_products.csv'

    def __init__(self, *args, **kwargs):
        super(JunoCoUkSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.start_brands_parsing, signals.spider_idle)
        
    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        categories = hxs.select("//div[@id='dj_equipment_landing_left']"
                                "//div[@class='dj_equipment_navigation_contents']"
                                "//div[@class='dj_equipment_navigation_records_text']"
                                "/a/@href").extract()

        for url in categories:
            url = urljoin_rfc(base_url, url)
            url = urljoin_rfc(base_url, url) + '?items_per_page=500'
            url = add_or_replace_parameter(url, 'show_out_of_stock', '1')
            url = add_or_replace_parameter(url, 'currency', 'GBP')
            yield Request(url, callback=self.parse_products)

    def start_brands_parsing(self, spider):
        if self != spider:
            return
        for url in self.start_urls:
            request = Request(url, callback=self.parse_brands)
            self.crawler.engine.crawl(request, self)
    
    def parse_brands(self, response):
        base_url = get_base_url(response)
        brands = response.xpath('//div[contains(., "Select a brand")]/select[@id]/option/@value').extract()
        for url in brands:
            url = urljoin_rfc(base_url, url)
            url = urljoin_rfc(base_url, url) + '?items_per_page=500'
            url = add_or_replace_parameter(url, 'show_out_of_stock', '1')
            url = add_or_replace_parameter(url, 'currency', 'GBP')
            yield Request(url, callback=self.parse_products)
        
    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select("//div[@class='breadcrumb_text']/*/text()").extract()[1:]
        products = hxs.select("//div[@class='product-list']//div[@class='dv-item']")

        for i, product in enumerate(products, 1):
            div_name = product.xpath('.//div[@class="vi-icon"][contains(.//span/@class, "glyphicon-w")]')
            name = div_name.xpath("./following-sibling::div[@class='vi-text'][1]/*//text()").extract_first()
            if not name:
                self.errors.append("No name found for product %d on page %s" % (i, response.url))
                continue
            url = div_name.xpath("./following-sibling::div[@class='vi-text'][1]/*//@href").extract_first()
            url = urljoin_rfc(base_url, url)
            identifier = url.split('/')[-2]
            image_url = "http://images.junostatic.com/full/IS" + str(identifier) + "-01-BIG.jpg"
            image_url = urljoin_rfc(base_url, image_url)
            price = product.select(".//span[@class='price_lrg']/text()").extract()
            price = extract_price(price[0])
            brand = product.select(".//a[contains(@href, 'labels')]"
                                   "[@class='text_medium text_subtle']/text()").extract()[0]
            # sku = ''.join(product.select('./following::tr[1]//td[@class="cat_no"]/span/text()').extract())
            stock = product.select(".//span[@id='curstock']/text()").re('\d+')
            if stock:
                stock = int(stock[0])
                stock = 1 if stock else 0
            else:
                stock = 0

            if not stock:
                continue

            loader = ProductLoader(item=Product(), selector=hxs)
            loader.add_value('name', name)
            loader.add_value('identifier', identifier)
            loader.add_value('url', url)
            loader.add_value('image_url', image_url)
            loader.add_value('price', price)
            # loader.add_value('sku', sku)
            loader.add_value('brand', brand)
            loader.add_value('stock', stock)
            for cat in categories:
                loader.add_value('category', cat)

            yield loader.load_item()

        pages = hxs.select("//div[@class='product_pagin']/a/@href").extract()
        for url in pages:
            url = add_or_replace_parameter(url, 'show_out_of_stock', '1')
            yield Request(url, callback=self.parse_products)
