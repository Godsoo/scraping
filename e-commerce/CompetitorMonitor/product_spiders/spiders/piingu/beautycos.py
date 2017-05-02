# -*- coding: utf-8 -*-

"""
Account: Piingu
Name: piingu-beautycos.dk
Ticket: https://app.assembla.com/spaces/competitormonitor/tickets/5000
"""


from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
from scrapy import Spider, Request
from decimal import Decimal
from product_spiders.utils import extract_price_eu
from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader,
)
# from itertools import product as iter_product


class PiinguBeautycosSpider(Spider):
    name = 'piingu-beautycos.dk'
    allowed_domains = ['beautycos.dk']
    start_urls = ['http://www.beautycos.dk']

    free_shipping_over = Decimal('650')

    def __init__(self, *args, **kwargs):
        super(PiinguBeautycosSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_idle, signals.spider_idle)

        self._finished_flg = False

    def spider_idle(self, spider):
        # Before spider finished we're going to scan the category lists
        # Maybe not all products are listed in brand lists
        if not self._finished_flg:
            self._finished_flg = True
            req = Request(self.start_urls[0],
                          dont_filter=True,
                          callback=self.parse_categories)
            self.crawler.engine.crawl(req, self)

    def start_requests(self):
        # First to parse the brand lists so that way we're gonna pick the brands up
        yield Request(self.start_urls[0],
                      callback=self.parse_brands)

    def parse_brands(self, response):
        brands = response.xpath('//div[@id="wo-tabs-1"]//ul[@id="nav"]/li/a')
        for brand_xs in brands:
            url = brand_xs.xpath('@href').extract()[0]
            brand = u''.join(brand_xs.xpath('.//text()').extract()).strip()
            yield Request(response.urljoin(url), callback=self.parse_list,
                          meta={'brand': brand})

    def parse_categories(self, response):
        categories = response.xpath('//div[@id="wo-tabs-2"]//ul[@id="nav"]/li/a/@href').extract()
        for url in categories:
            yield Request(response.urljoin(url), callback=self.parse_list,
                          meta={'brand': ''})

    def parse_list(self, response):
        # To list all products if they are not all already listed
        limiter_selected = response.xpath('//div[@class="limiter"]/select/option[@selected]/@value').extract()
        limiter_all = response.xpath('//div[@class="limiter"]/select/option[contains(@value, "limit=all")]/@value').extract()
        if limiter_all and limiter_selected:
            if limiter_selected[0] != limiter_all[0]:
                yield Request(response.urljoin(limiter_all[0]),
                              callback=self.parse_list,
                              meta=response.meta)

        sub_category_urls = response.xpath('//div[@class="category-item-center"]'
            '//span[@class="product-name"]/a/@href').extract()
        for url in sub_category_urls:
            yield Request(response.urljoin(url), callback=self.parse_list,
                          meta=response.meta)

        if not sub_category_urls:
            products = response.xpath('//ul[contains(@class, "products-grid")]/li[contains(@class, "item")]')
            for product_xs in products:
                product_name = ''.join(product_xs.xpath('.//*[contains(@class, "product-name")]//text()').extract()).strip()
                product_url = response.urljoin(product_xs.xpath(
                    './/*[contains(@class, "product-name")]//a/@href').extract()[0])
                product_price = extract_price_eu(product_xs.xpath('.//*[@class="price-box"]//text()').re(r'[\d\.,]+')[-1])
                product_image_url = map(response.urljoin, product_xs.xpath(
                    './/*[contains(@class, "product-image")]//img/@src').extract())
                product_brand = response.meta.get('brand', '')
                product_category = map(unicode.strip, response.xpath(
                    '//div[contains(@class, "breadcrumbs")]//li[contains(@class, '
                    '"category")]/a/text()').extract())[1:]
                product_out_of_stock = bool(product_xs.xpath(
                    './/*[contains(@class, "availability") and contains(@class, "out-of-stock")]'))
                product_shipping_cost = '0.00' if product_price >= self.free_shipping_over else '5.00'

                try:
                    product_identifier = product_xs.xpath('.//*[contains(@id, "product-price-")]/@id').re(r'(\d+)')[0]
                except:
                    product_identifier = None

                loader = ProductLoader(item=Product(), response=response)
                loader.add_value('name', product_name)
                loader.add_value('url', product_url)
                loader.add_value('price', product_price)
                loader.add_value('shipping_cost', product_shipping_cost)
                loader.add_value('image_url', product_image_url)
                loader.add_value('brand', product_brand)
                loader.add_value('category', product_brand or product_category)
                if product_out_of_stock:
                    loader.add_value('stock', 0)
                if product_identifier is not None:
                    loader.add_value('identifier', product_identifier)
                    loader.add_value('sku', product_identifier)
                    yield loader.load_item()
                else:
                    item = loader.load_item()
                    yield Request(item['url'], meta={'item': item}, callback=self.parse_options)

    def parse_options(self, response):
        main_id = response.xpath(
            './/div[@class="product-view" and @itemtype="http://schema.org/Product"]'
            '//div[@itemprop="offers"]//*[contains(@id, "product-price-")]/@id').re(r'(\d+)')
        if not main_id:
            main_id = response.xpath('.//*[contains(@id, "product-price-")]/@id').re(r'(\d+)')
        if not main_id:
            self.log('WARNING: No product identifier in => %s' % response.url)
            return
        main_id = main_id[0].strip()

        item = response.meta['item']

        main_price = response.xpath(
            './/div[@class="product-view" and @itemtype="http://schema.org/Product"]'
            '//div[@itemprop="offers"]//*[contains(@id, "product-price-")]/text()').re(r'[\d\.,]+')
        if main_price:
            item['price'] = extract_price_eu(main_price[0])

        item['identifier'] = main_id
        item['sku'] = main_id

        yield item

        """
        selectors = response.xpath('//select[contains(@id, "bundle-option-")]')
        if len(selectors) > 10:
            self.log('WARNING: Too many options in => %s' % response.url)
            return

        options = []
        for sel_xs in selectors:
            options.append(sel_xs.xpath('./option[not(@value="")]'))
        options = list(iter_product(*options))
        for opt_group in options:
            new_item = Product(item)
            for opt_xs in opt_group:
                opt_id = opt_xs.xpath('@value').extract()[0]
                opt_desc = opt_xs.xpath('text()').extract()[0]
                try:
                    opt_price = extract_price_eu(opt_desc.xpath('text()').re(r'\+[\d+\.]+,\d+')[0])
                except:
                    opt_price = Decimal('0.00')
                new_item['identifier'] += ':' + opt_id.strip()
                new_item['name'] += ' - ' + opt_desc.strip()
                if opt_price:
                    new_item['price'] = Decimal(new_item['price']) + opt_price
                yield new_item

        if not options:
            # No options found ...
            self.log('WARNING: No options found in => %s' % response.url)
        """
