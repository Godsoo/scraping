# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc


class ThomannDecksSpider(BaseSpider):
    name = u'decks_thomann.de'
    allowed_domains = ['thomann.de']
    start_urls = [
        u'http://www.thomann.de/gb/index.html',
    ]

    headers = {
        'User-agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.154 Safari/537.36'
    }
    download_delay = 1

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # categories
        urls = hxs.select('//div[contains(@class, "lr-navi-categories")]//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_subcategories)


    def parse_subcategories(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # subcategories
        urls = hxs.select('//li[@class="lr-cat-subcategories-category"]/a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_subcategories)
        # pagination
        try:
            next_page = hxs.select('//img[contains(@src, "pagination") and contains(@src, "right")]')
            next_page = next_page.select("./parent::div/parent::a/@href").extract()[0]
            yield Request(urljoin_rfc(base_url, next_page),
                          callback=self.parse_subcategories)
        except:
            pass
        # products
        products = hxs.select('//div[contains(@class, "search-entry")]')
        for product in products:
            brand = product.select('.//span[@class="manufacturerName"]/text()').extract()
            brand = brand[0] if brand else ''
            url = product.select('.//a[contains(@class,"articleLink")]/@href').extract()[0]
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_product,
                          meta={'brand': brand})


    def parse_product(self, response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        try:
            name = hxs.select('//h1[@itemprop="name"]/text()').extract()[0]
        except:
            return

        if not name and (hxs.select('//form[@id="coupon-purchaseForm"]') or hxs.select('//h1/../p[contains(text(), "is not part of our current product range anymore")]')):
            return

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_value('url', response.url)

        if 'B-STOCK' in name.upper():
            return

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
        price = hxs.select('//div[@class="tr-price-secondary"]/text()').extract()
        price = extract_price(price[0])
        loader.add_value('price', price)
        category = hxs.select('//ul[@class="tr-sidebar-categories-main"]/li/a/text()').extract()
        if category:
            loader.add_value('category', category[0])
        sku = hxs.select('//input[@name="ar"]/@value').extract()[0]
        loader.add_value('sku', sku)
        loader.add_value('identifier', sku)
        if int(price) <= 165:

            loader.add_value('shipping_cost', 8.3)
        yield loader.load_item()
