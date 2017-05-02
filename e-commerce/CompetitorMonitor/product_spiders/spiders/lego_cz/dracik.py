# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.contrib.loader.processor import Compose
from urlparse import urljoin
from product_spiders.items import Product, ProductLoader
import re
from product_spiders.utils import extract_price_eu as extract_price
from urlparse import urljoin as urljoin_rfc

from product_spiders.spiders.lego_cz.legobase import LegoMetadataBaseSpider


class DracikSpider(LegoMetadataBaseSpider):
    name = u'dracik.cz'
    allowed_domains = ['www.dracik.cz']
    start_urls = [
        u'http://www.dracik.cz/lego',
    ]
    errors = []

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # parse pagination
        urls = hxs.select('//*[@id="page-product-list"]//div[@class="paging"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse)
        # products list
        urls = hxs.select('//*[@id="obrazkove"]//h3/a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        try:
            name = hxs.select('//*[@id="product_title"]/text()').extract()[0].strip()
            price = hxs.select('//div[contains(@class,"rozpravkova-cena")]//div[@class="price-box"]/text()').extract()[0].strip()
        except:
            retry = int(response.meta.get('retry', 0))
            if retry < 10:
                new_meta = response.meta.copy()
                new_meta['retry'] = retry + 1
                yield Request(response.url, meta=new_meta, callback=self.parse_product, dont_filter=True)
            return

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_value('url', response.url)
        loader.add_value('name', name)
        loader.add_xpath('image_url', '//div[@class="image"]//img[@class="product"]/@src',
                         Compose(lambda v: urljoin(base_url, v[0])))
        price = extract_price(price.replace(' ', '').replace(u'\xa0', ''))
        loader.add_value('price', price)
        category = hxs.select(u'//*[@id="page-product-detail"]//div[@class="wrap_info"]//dl/dd/a[contains(@title, "Zna\u010dka")]/../preceding-sibling::dt/a/text()').extract()
        if category:
            loader.add_value('category', category[0])
        sku = hxs.select('//*[@id="parametry"]/div/table/tbody/tr[2]/td/text()').extract()
        if not sku:
            sku = ''
            for match in re.finditer(r"([\d,\.]+)", name):
                if len(match.group()) > len(sku):
                    sku = match.group()
        else:
            sku = sku[0]
        loader.add_value('sku', sku)
        identifier = hxs.select(u'//*[@id="page-product-detail"]//div[@class="wrap_info"]//dl/dd[contains(text(), "k\xf3d produktu")]/preceding-sibling::dt/text()').extract()[0]
        loader.add_value('identifier', identifier.strip())
        #availability = ''.join(hxs.select(u'//*[@id="page-product-detail"]//div[@class="wrap_info"]//dl/dd[contains(text(), "dostupnost eshop")]/preceding-sibling::dt/span/text()').extract()).strip()
        #if availability != u'na sklad\u011b':
        #    loader.add_value('stock', 0)
        loader.add_value('brand', 'LEGO')
        if int(price) <= 2500:
            loader.add_value('shipping_cost', 99)
        yield self.load_item_with_metadata(loader.load_item())
