# -*- coding: utf-8 -*-
import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc
#from scrapy.utils.url import add_or_replace_parameter


class SeneticSpider(BaseSpider):
    """
    WARNING!!!
    This spider uses cookiejar feature that requires scrapy v0.15
    That is why at the moment (17.07.2014) it is running on slave1 server
    which has scrapy 0.16 installed (default server has 0.14)
    """
    name = u'senetic.co.uk'
    allowed_domains = ['www.senetic.co.uk']
    start_urls = [
        'http://www.senetic.co.uk/'
    ]
    jar_counter = 0

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        urls = list(set(hxs.select('//div[@class="logo"]/parent::a/@href').extract()))
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_categories)

    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in hxs.select('//*[@id="tree"]//li[not(@class)]/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list)

    def parse_products_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)


        categories = hxs.select('//*[@id="tree"]//li[not(@class)]/a/@href').extract()
        categories += response.xpath('//*[@id="tree"]//li[contains(@class, "p3_nie")]/a/@href').extract()
        for url in categories:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list)

        for url in hxs.select('//*[@id="produkty"]//h2/a/@href').extract():
            self.jar_counter += 1
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_product,
                          cookies={},
                          meta={'cookiejar': self.jar_counter})

        next = hxs.select('//div[@class="pages"]/a[text()="next"]/@href').extract()
        if next:
            yield Request(urljoin_rfc(base_url, next[0]), callback=self.parse_products_list)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        price = hxs.select('//span[@class="cena_red"]/text()').extract()
        if not price:
            return
        if u'\xa0' in price[0]:
            price = price[0].split(u'\xa0')
        price = extract_price(price[0])
        loader.add_value('price', price)
        identifier = re.findall("ecomm_prodid: '(\d+)'", response.body)
        if not identifier:
            return
        loader.add_value('identifier', identifier[0])
        sku = hxs.select('//div[@class="product_pn_ean_brick"]/strong/text()').extract()
        if sku:
            loader.add_value('sku', sku[0])
        try:
            name = hxs.select('//*[@id="lewa"]/h1/text()').extract()[1].strip()
        except:
            name = ' '.join(hxs.select('//*[@id="lewa"]/h1/text()').extract()).strip()
            if not name:
                name = hxs.select('//*[@itemprop="name"]/text()').extract()[-1]
        url = response.url
        loader.add_value('url', urljoin_rfc(base_url, url))
        loader.add_value('name', name)
        image_url = hxs.select('//*[@id="lewa"]//a[@class="galeria"]/img/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        category = hxs.select('//*[@id="breadcrumbs"]//span[@class="breadcrumb_span"][3]//text()').extract()
        if category:
            loader.add_value('category', category[0])
        brand = hxs.select('//*[@id="breadcrumbs"]//span[@class="breadcrumb_span"][2]//text()').extract()
        if brand:
            loader.add_value('brand', brand[0])
        product = loader.load_item()
        yield product
    #     order = hxs.select('//a[@class="order_next_submit"]/@onclick').extract()
    #     if order:
    #         data = order[0].replace("'", '').replace('product_add2order(', '').split(',')
    #         url = add_or_replace_parameter(urljoin_rfc(base_url, '/product_add2order.php'), 'pid', data[0])
    #         url = add_or_replace_parameter(url, 'pn', data[1])
    #         url = add_or_replace_parameter(url, 'mode', '')
    #         url = add_or_replace_parameter(url, 'q', '1')
    #         url = add_or_replace_parameter(url, 'promo', '')
    #         yield Request(url,
    #                       method='POST',
    #                       headers={'X-Requested-With': 'XMLHttpRequest',
    #                                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'},
    #                       dont_filter=True,
    #                       meta={'product': product, 'cookiejar': response.meta['cookiejar']},
    #                       callback=self.parse_order)
    #     else:
    #         yield product
    #
    # def parse_order(self, response):
    #     yield Request('http://www.senetic.co.uk/order/',
    #                   dont_filter=True,
    #                   meta={'product': response.meta['product'], 'cookiejar': response.meta['cookiejar']},
    #                   callback=self.parse_shipping_price)
    #
    # def parse_shipping_price(self, response):
    #     hxs = HtmlXPathSelector(response)
    #     product = response.meta['product']
    #     shipping = hxs.select('//*[@id="total_delivery"]/text()').extract()
    #     if shipping:
    #         shipping = extract_price(shipping[0])
    #         product['shipping_cost'] = shipping
    #     yield product
