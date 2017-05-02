# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request

from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoader

import logging

def normalize_space(s):
    """ Cleans up space/newline characters """
    import re
    return re.sub('\\s+', ' ', s.replace(u'\xa0', ' ').strip())

class CampingworldCoUkSpider(BaseSpider):
    name = 'campingworld.co.uk'
    allowed_domains = ['campingworld.co.uk']
    start_urls = (
        'http://www.campingworld.co.uk/SetProperty.aspx?ShippingCountryID=1903&CurrencyISO=GBP&LanguageISO=en',
    )

    def parse(self, response):
        yield Request('http://www.campingworld.co.uk/BrandList.aspx',
                      callback=self.parse_brands)

    def parse_brands(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        brands = hxs.select('//table[@class="brand-list-table"]/tr/td/a/@href').extract()
        for url in brands:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products)

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        items = hxs.select("//table[@id='ProductDataList']/tr/td[div[contains(@id, 'ModelLinkCell')]]")
        for item in items:
            url = item.select(".//a[contains(@id, 'ModelLink')]/@href").extract()
            yield Request(urljoin_rfc(base_url, url[0]), callback=self.parse_product)

        pages = hxs.select('//div[@id="CustomPager1" and @class="results-pager"]//a/@href').extract()
        for page in pages:
            yield Request(urljoin_rfc(base_url, page), callback=self.parse_products)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        found = False
        for prod in hxs.select('//tr[contains(@class, "item-row")]'):
            found = True
            loader = ProductLoader(item=Product(), selector=prod)

            loader.add_xpath('identifier', './td[contains(@class, "item-stock-id")]/text()')
            loader.add_xpath('sku', './td[contains(@class, "item-stock-id")]/text()')
            loader.add_value('url', response.url)
            loader.add_value('name', normalize_space(' '.join(
                        hxs.select('//h1/text()').extract()
                        + prod.select('./td[contains(@class, "item-option-cell")]/a/text()').extract()
                        )))
            loader.add_xpath('price', './/span[@class="price-label"]/text()')
            loader.add_xpath('category', '//a[contains(@class, "history-menu-final-item")]/text()')
            img = hxs.select('//img[@id="ModelsDisplayStyle1_ImgModel"]/@src').extract()
            if img:
                loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

            loader.add_xpath('brand', '//a[@class="brand-image-link"]/@title')
            loader.add_xpath('shipping_cost', '//span[@id="ModelsDisplayStyle1_LblPostageCostValue"]/text()')

            if prod.select('//td[contains(text(), "In Stock")]'):
                loader.add_value('stock', '1')
            else:
                loader.add_value('stock', '0')
            yield loader.load_item()

        if not found:
            self.log("ERROR: No product on %s" % (response.url))


