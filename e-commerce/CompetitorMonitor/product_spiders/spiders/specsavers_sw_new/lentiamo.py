# -*- coding: utf-8 -*-
"""
Customer: Specsavers SW
Website: https://www.lentiamo.se
Extract all products, ignore these options http://screencast.com/t/mXLUdKkK0

Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5101

"""

import re

from scrapy.spider import SitemapSpider
from scrapy.http import HtmlResponse, Request

from product_spiders.spiders.specsavers_nz.specsaversitems import SpecSaversMeta


from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader


class Lentiamo(SitemapSpider):
    name = "specsavers_sw-lentiamo.se"
    allowed_domains = ["lentiamo.se"]
    start_urls = ['https://www.lentiamo.se/']
    
    sitemap_urls = ['https://www.lentiamo.se/robots.txt']
    sitemap_rules = [('', 'parse_products')]

    def parse(self, response):
        promotions = response.xpath('//a[contains(@href, "voucher")]/@href').extract()
        yield Request(response.urljoin(promotions[0]), callback=self.parse_promotions,
                      meta={'promotions': promotions[1:], 'dont_merge_cookies': True})

    def parse_promotions(self, response):
        """
        The site stores the promotion in the cookies so the spider extracts one promotion at a time.
        """
        promotions = response.meta.get('promotions', None)

        product_promotions = response.xpath('//a[contains(@href, "?voucher")]/@href').extract()
        for product_url in product_promotions:
            yield Request(product_url, callback=self.parse_product)

        if not promotions:
            for url in self.start_urls:
                yield Request(url, dont_filter=True, callback=self.parse_products)
        else:
            yield Request(response.urljoin(promotions[0]), callback=self.parse_promotions,
                          meta={'promotions': promotions[1:], 'dont_merge_cookies': True})

    def parse_products(self, response):
        for url in response.xpath('//div[@id="nav"]//a/@href').extract():
            yield Request(response.urljoin(url),  callback=self.parse_products)

        products = response.xpath('//a[@class="vc-product-item-link"]/@href').extract()
        products += response.xpath(u'//tr[contains(td/@data-thname, "Privat märke") or contains(td/@data-thname, "Originalmärke")]//a/@href').extract()
        for product in products:
            yield Request(response.urljoin(product), callback=self.parse_product, meta={'dont_merge_cookies': True})

        nextp = response.xpath('//p[@class="vc-pagination"]/a/@href').extract()
        if nextp:
            yield Request(response.urljoin(nextp[0]), callback=self.parse_products)
        
        if not products:
            for product in self.parse_product(response):
                yield product

    def parse_product(self, response):

        #replacement = response.xpath('//a[@class="replacementUrl" and not(@href="#") and not(@href="")]/@href').extract()
        #if replacement:
        #    yield Request(urljoin(base_url, replacement[0]), callback=self.parse_product)
        #    return

        name = response.xpath('//h1[@itemprop="name"]/text()').extract()
        name = ' '.join(name).strip()

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('name', name)
        loader.add_xpath('price', '//span[@itemprop="price"]/@content')
        loader.add_value('price', 0)
        image_urls = response.xpath('//div[@class="vc-detail-image-main"]/img/@srcset').extract()
        if image_urls:
            image_urls = map(lambda x:x.strip(), image_urls[0].split(' '))
            loader.add_value('image_url', image_urls[0])
        loader.add_xpath('brand', '//td[@itemprop="brand"]/meta/@content')
        category = response.xpath('//tr[contains(th/text(), "Kategori")]/td/a/text()').extract()
        if category:
            loader.add_value('category', category)
        loader.add_value('url', response.url)

        identifier = response.xpath('//input[@name="productId"]/@value').extract_first()
        if not identifier:
            return

        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)

        metadata = SpecSaversMeta()
        promotion = re.findall("var cartDiscount = '(.*): ", response.body)
        promotion = promotion[0] if promotion else ''
        metadata['promotion'] = promotion

        item = loader.load_item()
        item['metadata'] = metadata
        yield item

