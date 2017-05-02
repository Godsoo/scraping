# -*- coding: utf-8 -*-

from scrapy.spider import BaseSpider
from scrapy import log
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy.contrib.loader.processor import Compose, TakeFirst


from product_spiders.items import Product, ProductLoader


STOCK_MAP = {
    # Product is available in very small amount
    u'Produkt dostępny w bardzo małej ilości': 1,

    # Product is available in a small amount
    u'Produkt dostępny w małej ilości': 1,

    # Product is available in very large amount
    u'Produkt dostępny w bardzo dużej ilości': 1,

    # Product is available in large amount
    u'Produkt dostępny w dużej ilości': 1,

    # Product is available
    u'Produkt na zamówienie': 1,

    # Presale
    u'Przedsprzedaż': 1,

    # Product not available
    u'Produkt niedostępny': 0,
}


class DkwadratPl(BaseSpider):
    name = 'voga_pl-dkwadrat.pl'
    allowed_domains = ['www.dkwadrat.pl']
    start_urls = ('http://www.dkwadrat.pl/',)
    download_delay = 1

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        # categories
        categories = hxs.select('//div[@id="menu_categories2"]//li/a/@href').extract()
        for url in categories:
            url = urljoin_rfc(get_base_url(response), url)
            if '/product-pol-' in url:
                yield Request(url, callback=self.parse_product)
            elif '/pol_m_' in url:
                yield Request(url, callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)

        # products
        products = hxs.select(u'//div[@id="search"]//a[@class="product_name"]/@href').extract()
        for url in products:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product)

        if not products:
            meta = response.meta.copy()
            meta['retry'] = meta.get('retry', 0)
            if meta['retry'] < 3:
                meta['retry'] += 1
                self.log('>>> RETRY %d => %s' % (meta['retry'], response.request.url))
                yield Request(response.request.url, meta=meta)

        # pages
        next_page = hxs.select(u'/html/head/link[@rel="next"]/@href').extract()
        if next_page:
            url = urljoin_rfc(get_base_url(response), next_page[0])
            yield Request(url, callback=self.parse_category)

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return

        hxs = HtmlXPathSelector(response)
        category = hxs.select(u'//div[@id="breadcrumbs_sub"]/ol/li/a[@class="category"]/text()').extract()
        category = category[0] if category else ''
        image_url = hxs.select(u'//form[@id="projector_form"]//img[@itemprop="image"]/@src').extract()
        if image_url:
            image_url = urljoin_rfc(get_base_url(response), image_url[0])

        name = hxs.select(u'//div[@id="breadcrumbs"]//li[last()]/span/text()').extract()[0]
        name_option = hxs.select(u'//div[@class="product_section_sub"]/a[@title and contains(@class, "active")]/@title')
        if name_option:
            name = "%s - %s" % (name.rstrip(),
                                name_option.extract()[0].lstrip())

        product_loader = ProductLoader(item=Product(), response=response)
        product_loader.add_value('name', name.strip())
        product_loader.add_value('url', response.url)
        product_loader.add_value('category', category)
        product_loader.add_value('image_url', image_url)

        identifier = hxs.select(u'//form[@id="projector_form"]/input[@name="product"]/@value').extract()

        product_loader.add_value('identifier', identifier[0])
        price_xpath = '//div[@id="projector_price_value_wrapper"]/strong/span[@class="price"]/text()'
        product_loader.add_xpath('price', price_xpath)
        product_loader.add_xpath('shipping_cost',
                                 '//div[@id="projector_shipping"]/span/text()',
                                 TakeFirst(),
                                 Compose(lambda v: v.replace(',', '.')), re='([0-9.]+)')
        stock_option = hxs.select(u'//div[@id="projector_status_description"]/text()').extract()
        self.log("Stock option found %s" % stock_option, level=log.DEBUG)
        product_loader.add_value('stock', STOCK_MAP.get(stock_option[0], 0))
        yield product_loader.load_item()

        # parse product options
        more_products = hxs.select(u'//div[@class="product_section_sub"][1]/a[@title]/@href').extract()
        _, _, urlpath = response.url.partition('/product-pol')
        url_to_remove = "/product-pol%s" % urlpath
        final_more_products = list(set(more_products) - set([url_to_remove]))

        # parse product
        for product_url in final_more_products:
            product_url = urljoin_rfc(get_base_url(response), product_url)
            yield Request(product_url, callback=self.parse_product)
