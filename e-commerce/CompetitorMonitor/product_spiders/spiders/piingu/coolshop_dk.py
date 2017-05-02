# -*- coding: utf-8 -*-
import re
import json

from scrapy.spider import BaseSpider
from scrapy.http import Request, FormRequest
from scrapy.selector import HtmlXPathSelector, Selector
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price_eu



class CoolshopDkSpider(BaseSpider):
    name = 'piingu-coolshop.dk'
    allowed_domains = ['coolshop.dk']
    start_urls = ('https://www.coolshop.dk/',)
    errors = []

    def parse(self, response):
        categories = response.xpath('//nav[@class="nav"]//a/@href').extract()
        for category in categories:
            yield Request(response.urljoin(category), callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)

        categories = response.xpath(u'//div[@id="search-content-container"]//div[contains(@class, "campaign-block")]//a/@href').extract()
        for category in categories:
            yield Request(response.urljoin(category), callback=self.parse_category)
        
        try:
            total = int(response.xpath('//header[@id="search-header"]//span[@class="qty"]/text()').re(r'\((\d+)\)').pop())
        except:
            return
        csrf_token = response.xpath('//form[@id="newsletterform"]//input[@name="csrfmiddlewaretoken"]/@value').extract()[0]
        new_relic_id = re.search(r'loader_config=\{xpid:"(.*?)"\}', response.body)
        new_relic_id = new_relic_id.group(1) if new_relic_id else ''

        headers = {
            'Host': 'www.coolshop.dk',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'X-NewRelic-ID': new_relic_id,
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-CSRFToken': csrf_token,
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': response.url,
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
        }

        response.meta['ajax_headers'] = headers
        response.meta['current_start'] = 0
        response.meta['total'] = total

        for item in self.parse_products(response):
            yield item

    def parse_products(self, response):
        try:
            data = json.loads(response.body)
            hxs = Selector(text=data['html'])
        except:
            hxs = Selector(response)

        meta = response.meta.copy()
        if (int(meta['current_start']) + 30) < int(meta['total']):
            meta['current_start'] = int(meta['current_start']) + 30
            form_request = FormRequest(response.url,
                formdata={'start': str(meta['current_start'])},
                headers=meta['ajax_headers'],
                dont_filter=True,
                meta=meta,
                callback=self.parse_products)
            yield form_request

        products = hxs.css('.productitem a::attr(href)').extract()
        for url in products:
            yield Request(response.urljoin(url),
                          callback=self.parse_product,
                          meta={'dont_merge_cookies': True})

    def parse_product(self, response):
        base_url = get_base_url(response)

        options = response.xpath('//div[@id="product-variants"]//a/@href').extract()
        for option in options:
            yield Request(response.urljoin(option), callback=self.parse_product)


        product_loader = ProductLoader(item=Product(), response=response)
        in_stock = response.xpath('//div[contains(@class, "product-stock")]/div/@data-stock').extract()
        if not in_stock:
            product_loader.add_value('stock', 0)
        elif 'in-stock' not in in_stock[0] or 'not-in-stock' in in_stock[0]:
            product_loader.add_value('stock', 0)

        

        identifier = response.xpath('//td[@itemprop="sku"]/text()').extract_first()
        image_url = response.xpath('//a[@rel="productImages" and @class="image"]/@href').extract()[-1]

        product_name = response.css('.product-title h1::text').extract_first()
        active_options = response.xpath('//div[@id="product-variants"]//a[contains(@class, "active")'
                                        ' and not(contains(@class, "deactive"))]/text()').extract()
        if active_options:
            active_options = map(lambda x: x.strip(), active_options)
            product_name += ' ' + ' '.join(active_options)

        sku = response.xpath('//td[@itemprop="productID"]/text()').extract()
        sku = sku[0].strip() if sku else ''
        identifier = identifier or sku
        if not identifier:
            self.logger.error('No identifier found on %s' %response.url)
            return

        categories = response.xpath('//div[@id="breadcrumb"]//a/text()').extract()[-3:]

        product_loader.add_value('identifier', identifier)
        product_loader.add_value('image_url', response.urljoin(image_url))
        product_loader.add_value('name', product_name)
        product_loader.add_value('sku', sku)
        product_loader.add_value('url', response.url)
        product_loader.add_value('category', categories)
        product_loader.add_xpath('brand', '//h2[@class="product-brand"]/a/text()')

        price = response.xpath('//meta[@property="product:price:amount"]/@content').extract_first()
        if price:
            product_loader.add_value('price', price)
        else:
            product_loader.add_value('price', 0)
            product_loader.add_value('stock', 0)

        yield product_loader.load_item()
