# -*- coding: utf-8 -*-

from scrapy.spider import BaseSpider

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc


class OncallmedicalsuppliesSpider(BaseSpider):
    name = u'thomann.de'
    allowed_domains = ['thomann.de']
    start_urls = [
        u'http://www.thomann.de/gb/index.html',
    ]

    headers = {
        'User-agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.154 Safari/537.36'
    }

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # categories
        urls = hxs.select('//ul[@class="lr-index-categories-list"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_subcategories)

    def parse_subcategories(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # subcategories
        urls = hxs.select('//ul[contains(@class, "lr-cat-subcategories")]//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_subcategories)
        # pagination
        urls = hxs.select('//div[@id="resultPageNavigation"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_subcategories)
        # products
        products = hxs.select('//div[contains(@class, "search-entry")]')
        for product in products:
            brand = product.select('.//span[@class="manufacturerName"]/text()').extract()
            brand = brand[0] if brand else ''
            url = product.select('.//a[@class="lr-articlelist-article-articleLink"]/@href').extract()[0]
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_product,
                          meta={'brand': brand})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        name = hxs.select('//h1[@itemprop="name"]/text()').extract()
        if not name:
            return
        name = name.pop().strip()
        loader.add_value('url', response.url)
        loader.add_value('name', name)
        loader.add_value('brand', response.meta.get('brand'))
        image_url = hxs.select('//img[@itemprop="image"]/@src').extract()
        if image_url:
            image_url = 'http://images5.thomann.de/pics/prod/' + image_url[0].split('/')[-1]
            loader.add_value('image_url', image_url)
        available = ''.join(hxs.select('//div[contains(@class,"tr-prod-availability")]/text()').extract()).strip().upper()
        if available:
            if 'AVAILABLE IMMEDIATELY' not in available.upper():
                loader.add_value('stock', 0)
        price = response.xpath('//span[@class="secondary"]/text()').extract()[0]
        price = extract_price(price)
        loader.add_value('price', price)
        category = response.xpath('//li[normalize-space(@class)="lr-breadcrumb-stage"]/a/text()').extract()
        if category:
            loader.add_value('category', category[1])
        sku = hxs.select('//input[@name="ar"]/@value').extract()[0]
        loader.add_value('sku', sku)
        loader.add_value('identifier', sku)
        if int(price) <= 165:
            loader.add_value('shipping_cost', 8.3)
        yield loader.load_item()
