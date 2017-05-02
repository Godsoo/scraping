# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc
import demjson

from product_spiders.spiders.pedalpedal.crcitem import CRCMeta


class JensonusaSpider(BaseSpider):
    name = u'jensonusa.com'
    allowed_domains = ['www.jensonusa.com']
    start_urls = [
        'http://www.jensonusa.com/Category'
    ]
    errors = []
    download_delay = 0.5

    def retry(self, response, error="", retries=3):
        meta=response.meta
        retry = int(meta.get('retry', 0))
        if retry < retries:
            retry = retry + 1
            meta['retry'] = retry
            meta['recache'] = True
            yield Request(response.request.url, dont_filter=True,
                          meta={'retry': retry}, callback=response.request.callback)
        else:
            self.errors.append(error)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in hxs.select('//div[@class="cat-list-bdy"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url + '?pg=100'), callback=self.parse_products_list)

    def parse_products_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in hxs.select('//div[@class="prlist-itm-content"]//a[@href!="javascript: void(0);"]/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)
        next_page = response.xpath('//div[@class="pagerpagenum"]//a[span[@class="jenson-icon-arrow-right"]]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]), callback=self.parse_products_list)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        product_identifier = hxs.select('//@prodid').extract()
        if product_identifier:
            product_identifier = product_identifier[0].strip()
        else:
            self.retry(response, "Cant find identifier on " + response.url)
            return
        image_url = hxs.select('//div[@class="prod-images-container"]//img/@src').extract()
        product_name = hxs.select('//div[@class="product-name"]//h1/text()').extract()[0].strip()
        category = hxs.select('//*[@id="bcrumb"]/a[2]/text()').extract()
        category = category[0].strip() if category else ''
        brand = hxs.select('//div[contains(@class, "product-brand-icon")]/a/img/@alt').extract()
        brand = brand[0].strip() if brand else ''
        #uname = hxs.select('//input[@id="hdnUName"]/@value').extract()[0]
        option_title = response.css('.prod-selector-section-hdr').xpath('text()').extract_first()
        size_or_color = 'Color' in option_title or 'Size' in option_title
        options = response.xpath('//div[@id="dropdownSkuCtrl_nojs"]//option')
        js_options = response.xpath('//script[contains(., "arrSku")]/text()').re('({.+?});')
        js_options = {demjson.decode(opt)['skuID']: demjson.decode(opt) for opt in js_options}
        for option in options:
            product_loader = ProductLoader(item=Product(), selector=option)
            sku = option.select('./@skucode').extract()
            if not sku:
                continue
            sku = sku[0]
            product_loader.add_value('sku', sku)
            identifier = option.select('./@value').extract()[0]
            if identifier not in js_options:
                continue
            product_loader.add_value('identifier', product_identifier + '_' + identifier)
            option_name = js_options[identifier]['color'].title() + ', ' + js_options[identifier]['size'].title()
            if option_name.startswith(', '):
                option_name = option_name[2:]
            if option_name.endswith(', '):
                option_name = option_name[:-2]
            if not option_name:
                if size_or_color:
                    continue
                option_name = option.select('./text()').extract()[0].strip()
            product_loader.add_value('name', product_name + ', ' + option_name)
            attcolor = option.select('./@attcolor').extract()
            if attcolor:
                attcolor = attcolor[0]
                image_url = hxs.select('//div[@attcolor="{}"]/@lrgimg'.format(attcolor)).extract()
            if image_url:
                product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            price = extract_price(option.select('./@adjdefprice').extract()[0])
            product_loader.add_value('price', price)
            product_loader.add_value('url', response.url)
            product_loader.add_value('brand', brand)
            product_loader.add_value('category', category)
            skustatus = option.select('./@skustatus').extract()[0]
            if skustatus == 'INVUVL':
                product_loader.add_value('stock', 0)
            product = product_loader.load_item()

            prcoff = extract_price(''.join(option.select('./@prcoff').extract()))
            rrp = option.select('./@retailprice').extract()
            rrp = extract_price(rrp[0])
            rrp = str(rrp) if rrp>price else ''
            metadata = CRCMeta()
            metadata['rrp'] = rrp
            product['metadata'] = metadata

            yield product
