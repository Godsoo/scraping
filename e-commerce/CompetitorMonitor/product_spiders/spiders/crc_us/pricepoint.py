# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc

from product_spiders.spiders.pedalpedal.crcitem import CRCMeta

class PricepointSpider(BaseSpider):
    name = u'pricepoint.com'
    allowed_domains = ['www.pricepoint.com']
    start_urls = [
        'http://www.pricepoint.com/'
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in response.css('.nav a::attr(href)').extract():
            yield Request(urljoin_rfc(base_url, url + '?page_no=1&page_length=9999'), callback=self.parse_product_list)

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        #pagination
        for url in hxs.select('//ul[@class="paging"]//a[@class="next-li"]/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product_list)
        #products
        category = hxs.select('//div[@class="main-holder"]//h1/text()').extract()[0]
        for url in hxs.select('//div[@class="item"]//strong[@class="title"]/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta={'category': category})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        product_name = hxs.select('//h1[@itemprop="name"]/text()').extract()[0].strip()
        category = response.meta['category']
        brand = hxs.select('//ul[@class="breadcrumbs"]/li/a/text()').extract()
        brand = brand.pop().strip() if brand else ''
        image_urls = hxs.select('//a[@class="alternate-image" and contains(@href, "_0")]/@href').extract()

        options = response.xpath('//select[@id="ProductStyles"]//option')
        if options:
            for option in options[1:]:
                product_loader = ProductLoader(item=Product(), selector=option)
                sku = option.select('./@item_number').extract()[0]
                product_loader.add_value('sku', sku)
                identifier = option.select('./@value').extract()[0]
                product_loader.add_value('identifier', identifier)
                option_name = option.select('./text()').extract()[0].strip()
                option_name = option_name.replace(u' »', ',').replace('\\"', '"')
                product_loader.add_value('name', product_name + ', ' + option_name)
                code = option.select('./@level2code').extract()[0].lower()
                for image_url in image_urls:
                    if code in image_url:
                        product_loader.add_value('image_url', urljoin_rfc(base_url, image_url))
                        break
                price = option.xpath('@offer_price').extract_first() or option.xpath('@price').extract_first()
                product_loader.add_value('price', price)
                product_loader.add_value('url', response.url)
                product_loader.add_value('brand', brand)
                product_loader.add_value('category', category)
                stock = int(option.select('./@available_inventory').extract()[0])
                stock = 0 if stock < 0 else stock
                product_loader.add_value('stock', stock)
                product = product_loader.load_item()
                rrp = ''.join(option.select('./@msrp').extract())
                metadata = CRCMeta()
                metadata['rrp'] = rrp
                product['metadata'] = metadata
                yield product
        else:
            product_loader = ProductLoader(item=Product(), selector=hxs)
            sku = hxs.select('//span[@itemprop="productID"]/text()').extract()[0]
            product_loader.add_value('sku', sku)
            identifier = hxs.select('//*[@id="AddToCartForm"]/input/@value').extract()[0]
            product_loader.add_value('identifier', identifier)
            price = hxs.select('//dd[@id="Price_{}"]/text()'.format(identifier)).extract()
            if not price:
                price = hxs.select('//dd[@id="OfferPrice_{}"]/text()'.format(identifier)).extract()
            product_loader.add_value('price', extract_price(price[0].strip()))
            product_loader.add_value('name', product_name)
            product_loader.add_value('url', response.url)
            product_loader.add_value('brand', brand)
            product_loader.add_value('category', category)
            image_url = hxs.select('//*[@id="MainImage"]/@src').extract()
            if image_url:
                product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            stock = hxs.select('//span[@class="stock-status"]/text()').extract()
            if stock:
                stock = stock[0].strip()
                if 'IN STOCK' in stock:
                    try:
                        stock = int(stock.replace('IN STOCK', '').strip())
                    except:
                        if stock != 'IN STOCK':
                            self.log("WARNING!!! Stock: {} URL: {}".format(stock, response.url))
                    else:
                        product_loader.add_value('stock', stock)
                else:
                    self.log("WARNING!!! Stock: {} URL: {}".format(stock, response.url))
            product = product_loader.load_item()
            rrp = str(extract_price(''.join(hxs.select('//dd[@class="p-reg"]/text()').extract())))
            metadata = CRCMeta()
            metadata['rrp'] = rrp
            product['metadata'] = metadata
            yield product
