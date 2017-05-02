# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy import log
import re


class GardengearRuSpider(BaseSpider):
    name = u'gardengear_ru'
    allowed_domains = ['gardengear.ru']
    start_urls = [
        'http://gardengear.ru/catalog/'
    ]
    l_urls = []

    identifiers = []

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for cond in ['//div[@class="b-catalog-sections"]//ul[@class="b-catalog-subsections__inner"]/li',
                     '//div[@class="b-catalog-sections"]//ul[contains(@class, "b-catalog-subsections__inner__more")]/li']:
            for cats in hxs.select(cond):
                urls = cats.select('.//ul[@class="b-catalog-subsections__inner__sub"]/li/a/@href')
                if urls:
                    for url in urls.extract():
                        yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list, meta={'page': 1, 'p1': ''})
                else:
                    url = cats.select('./a/@href').extract()
                    if url:
                        yield Request(urljoin_rfc(base_url, url[0]), callback=self.parse_products_list, meta={'page': 1, 'p1': ''})

    def parse_products_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        subcats = hxs.select('//div[@class="b-catalog-sections"]//a/@href')
        if subcats:
            for url in list(set(subcats.extract())):
                yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list, meta={'page': 1, 'p1': ''})
        else:
            category = hxs.select('//h1[@class="b-red-title"]/text()')
            if category:
                category = ''.join(category.extract()).strip()
            # items = hxs.select('//section[contains(@class, "b-product-list")]//div[@class="b-product-item  clearfix"]')
            items = hxs.select('//section[contains(@class, "b-product-list")]/div[contains(@class,"b-product-item")]')
            if items:
                cnt = len(items)
                if cnt >= 1:
                    # last item url
                    l_url = items[-1].select('.//div[@class="b-product-item__name"]//a[@class="b-product-item__link"]/@href').extract()[0]
                    if l_url not in self.l_urls:
                        self.l_urls.append(l_url)
                        for url in items:
                            p_url = url.select('.//div[@class="b-product-item__name"]//a[@class="b-product-item__link"]/@href').extract()[0]
                            if not url.select('.//div[@class="b-product-item__status"]/span[contains(@class, "b-product_item__status_text-790")]'):
                                yield Request(urljoin_rfc(base_url, p_url), callback=self.parse_product, meta={'category': category})
                            else:
                                log.msg(p_url + " OUTPROD")
                        # p1 = response.meta['p1']
                        # if p1 == '':
                        p1 = l_url
                        yield Request(re.sub(r'\?.*','',response.url) + "?PAGEN_1=" + str(response.meta['page'] + 1), callback=self.parse_products_list, meta={'page': response.meta['page'] + 1, 'p1': p1})
                    else:
                        log.msg(response.url + ' SAME PAGE AGAIN')
                else:
                    for url in items:
                        p_url = url.select('.//div[@class="b-product-item__name"]//a[@class="b-product-item__link"]/@href').extract()[0]
                        if not url.select('.//div[@class="b-product-item__status"]/span[contains(@class, "b-product_item__status_text-790")]'):
                            yield Request(urljoin_rfc(base_url, p_url), callback=self.parse_product, meta={'category': category})
                        else:
                            log.msg(p_url + " OUTPROD")


    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        product_data = hxs.select('//section[contains(@class, "i-product_page")]').extract()
        if product_data:
            for product in self.parse_product_data(response.url, get_base_url(response), product_data[0], response.meta['category']):
                if product['identifier'] not in self.identifiers:
                    self.identifiers.append(product['identifier'])
                    yield product

    def parse_product_data(self, url, base_url, product_data, category):
        hxs = HtmlXPathSelector(text=product_data)
 
        image_url = hxs.select('//div[@class="b-product-image"]/a[@class="fancybox-detail_image"]/@href').extract()
        product_sku = hxs.select('//div[@class="b-product-article__item"]/text()').re(': (.*)')
        if product_sku:
            product_sku = product_sku[0].strip()
        product_identifier = hxs.select('//a[@id="opener"]/@data_id').extract()
        if not product_identifier:
            product_identifier = hxs.select('//button[@id="send_button_0"]/@data-pid').extract()
        if not product_identifier:
            product_identifier = product_sku
        if not product_identifier:
            log.msg(url + ' NO ID')
            return
        product_name = hxs.select('//h1/text()').extract()[0].strip()
        brand = hxs.select('//div[@class="b-breadcrumb_manuf"]/ul/li/a[@class="b-breadcrumb__link"]/text()').extract()
        brand = brand[1].strip() if brand else ''
        stock = 0
        avail = hxs.select('//div[@class="b-product-status"]/span[contains(@class, "b-product_item__status_text-789") or contains(@class, "b-product_item__status_text-32")]').extract()
        if avail:
            stock = None

        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('identifier', product_identifier)
        product_loader.add_value('name', product_name)
        product_loader.add_value('sku', product_sku)
        product_loader.add_value('stock', stock)
        if image_url:
            product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        price = hxs.select('//div[@class="b-product__price_inactive"]//text()').extract()
        if price:
            product_loader.add_value('price', price[0].strip().replace(" ",""))
        else:
            product_loader.add_value('price', "")
        product_loader.add_value('url', url)
        product_loader.add_value('brand', brand)
        product_loader.add_value('category', category)
        product = product_loader.load_item()
        yield product
