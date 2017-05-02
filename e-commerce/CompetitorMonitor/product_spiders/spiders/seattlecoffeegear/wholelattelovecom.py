import re
import logging
from copy import copy

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy import log

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)


class WholelatteloveComSpider(BaseSpider):
    name = 'wholelattelove.com'
    allowed_domains = ['wholelattelove.com']
    start_urls = ('http://www.wholelattelove.com/', )# 'http://www.wholelattelove.com/brands')

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        # brands
        # brands = hxs.select('//a[contains(@href,"brand")]/@href').extract()
        # for url in brands:
            # url = urljoin_rfc(base_url, url.strip())
            # yield Request(url)

        # categories
        category_urls = hxs.select('//ul[@class="nav"]//a/@href').extract()
        for url in category_urls:
            url = urljoin_rfc(base_url, url.strip())
            yield Request(url)

        # pagesproductlistsortfloatleft
        pages_urls = set(hxs.select('//nav[@class="pagination"][1]/span/a/@href').extract())
        for url in pages_urls:
            url = urljoin_rfc(base_url, url.strip())
            yield Request(url)
        # products list
        products = hxs.select('//div[@id="products"]/div')
        if not products:
            log.msg("ERROR!! NO PRODUCTS!! %s " % response.url)
            logging.error("ERROR!! NO PRODUCTS!! %s" % response.url)
        for product_el in products:
            name = product_el.select('.//a//span[@class="name"]/text()').extract()
            if not name:
                continue

            url = product_el.select('.//a[descendant::span[@class="name"]/text()]/@href').extract()
            if not url:
                log.msg("ERROR!! NO URL!! %s" % response.url)
                continue
            url = url[0]
            url = urljoin_rfc(base_url, url.strip())

            price = set([p.strip() for p in product_el.select('.//span[@class="price" or @class="sale"]/text()').extract() if p.strip()])
            if not price:
                log.msg("ERROR!! NO PRICE!! %s" % response.url)
                price = '0.00'
            price = price.pop()

            sku = product_el.select('./@data-product-id').extract()
            if not sku:
                log.msg("ERROR!! NO SKU!! %s" % response.url)
                continue
            product = Product()
            loader = ProductLoader(item=product, response=response)
            loader.add_value('url', url)
            loader.add_value('name', name)
            loader.add_value('price', price)
            loader.add_value('sku', sku[0])
            loader.add_value('identifier', sku[0])
            yield Request(loader.get_output_value('url'), callback=self.parse_product, meta={'loader': loader})

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        loader = response.meta.get('loader')

        image_url = hxs.select('//img[@itemprop="image"]/@src').extract()
        if image_url:
            image_url = urljoin_rfc(base_url, image_url[0])
            loader.add_value('image_url', image_url)

        category = hxs.select('//ol[contains(@class, "breadcrumb")]/li/a/span/text()').extract()
        if category:
            loader.add_value('category', category[-2] if len(category) > 1 else category[-1])

        brand = hxs.select('//meta[@name="product-brand"]/@content').extract()
        if brand:
            loader.add_value('brand', brand[0])

        options = hxs.select('//div[@class="options"]//option')
        for option in options:
            loader = copy(loader)
            p = loader.load_item()
            stock = option.select('./@data-stock').extract()
            if stock and stock[0] != "in_stock":
                p['stock'] = 0
            p['identifier'] += '.%s' % option.select('./@value').extract().pop()
            p['name'] += ' %s' % option.select('./text()')[0].extract().strip()
            p['price'] = option.select('./@data-price')[0].extract()
            yield p
        if not options:
            stock = hxs.select('//meta[@itemprop="availability"][@content="in_stock"]')
            if not stock:
                loader.add_value('stock', 0)
            yield loader.load_item()
