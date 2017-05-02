import re
import logging
import urllib

from decimal import Decimal
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product
from axemusic_item import ProductLoader

from scrapy import log


class StevesMusicComSpider(BaseSpider):
    name = 'stevesmusic.com'
    allowed_domains = ['stevesmusic.com']
    start_urls = ('http://www.stevesmusic.com',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select(u'//li[@class="category-top_un"]/span/a/@href').extract():
            yield Request(url, callback=self.parse_product_list)

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select(u'//li[@class="category-top_un"]/span/a/@href').extract():
            yield Request(url, callback=self.parse_product_list)

        for url in hxs.select(u'//table[@class="two-column-listing"]//tr/td/a/@href').extract():
            yield Request(url, callback=self.parse_product_list)

        for url in hxs.select(u'//h3[@class="itemTitle"]/a/@href').extract():
            yield Request(url, callback=self.parse_product)

        next_page = hxs.select(u'//a[contains(@title,"Next Page")]/@href').extract()
        if next_page:
            yield Request(next_page[0], callback=self.parse_product_list)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('url', response.url)
        product_loader.add_xpath('name', u'//div[@itemprop="name"]/text()')
        price = hxs.select(u'//span[@itemprop="price"]/text()').extract()
        price = price[0] if price else '0'
                
        product_loader.add_value('price', price)

        product_id = hxs.select(u'//form//input[@type="hidden" and @name="products_id"]/@value').extract()
        if not product_id:
            product_id = hxs.select('//div[@id="productTellFriendLink"]/a/@href').re('products_id=(.*)')
            if not product_id:
                product_id = re.findall(r'products_id=(.*)" class', response.body)
                if not product_id:
                    log.msg('Product without identifier: '+ response.url)
                    return

        product_loader.add_value('identifier', product_id[0])

        sku = hxs.select(u'//span[@itemprop="identifier"]/text()').extract()
        if sku:
            product_loader.add_value('sku', sku[0])

        product_loader.add_xpath('category', u'//div[@id="navBreadCrumb"]/a[2]/text()')

        img = hxs.select(u'//div[@id="productMainImage"]//img/@src').extract()
        if img:
            img = urljoin_rfc(get_base_url(response), img[0])
            product_loader.add_value('image_url', img)

        brand = hxs.select('//li[@itemprop="brand"]/text()').extract()
        if brand:
            brand = brand[0].replace('Manufactured by: ', '')
            product_loader.add_value('brand', brand)

        product = product_loader.load_item()
        if product['price'] > 0:
            yield product
        """
        if hxs.select(u'//div[@class="wrapperAttribsOptions"]'):
            opts = hxs.select(u'//div[@class="wrapperAttribsOptions"]/div//label/text()').extract()
            if not opts:
                opts = hxs.select(u'//div[@class="wrapperAttribsOptions"]/div//option/text()').extract()
            for opt in opts:
                p = Product(product)
                try: 
                    if '$' in opt:
                        name, price = opt.split('(')[:2]
                    else:
                        name, price = opt, None
                except: name, price = opt, None
                p['name'] = p['name'] + ' ' + name.strip()
                if price:
                    pricen = price.replace(')', '').replace('C', '').replace('$', '').replace(',', '').strip()
                    if pricen.startswith('+'):
                        p['price'] = p['price'] + Decimal(pricen[1:])
                    else:
                        p['price'] = Decimal(pricen)
                yield p
        # http://www.stevesmusic.com/index.php?main_page=product_info&cPath=2_27_103&products_id=7059 ?
        else:
            yield product
        """
