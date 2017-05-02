import re
import logging
import urllib

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter

from scrapy import log

from product_spiders.items import Product
from axemusic_item import ProductLoader


class LaMusicCaSpider(BaseSpider):
    name = 'lamusic.ca'
    allowed_domains = ['lamusic.ca']
    start_urls = ('http://www.lamusic.ca',)

    def start_requests(self):
        yield Request('http://www.lamusic.ca/SearchResults.asp?searching=y&sort=7&Search=%25%25&sort=13',
                      callback=self.parse_product_list)

        for url in self.start_urls:
            yield Request(url)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        for url in hxs.select(u'//div[@id="display_menu_s"]/ul/li/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product_list)

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        pages = re.findall(r'\b\d+\b', ''.join(hxs.select('//nobr/font/b/font/b/text()').extract()))
        if pages:
            for i in range(1, int(pages[0]) + 1):
                yield Request(add_or_replace_parameter(response.url, 'page', str(i)), callback=self.parse_product_list)

        sub_categories = hxs.select('//a[@class="subcategory_link"]/@href').extract()
        for sub_cat in sub_categories:
            url = add_or_replace_parameter(sub_cat, 'searching', 'Y')
            url = add_or_replace_parameter(url, 'show', '400')
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product_list)

        for url in hxs.select(u'//a[contains(@class,"productnamecolor")]/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('url', response.url)
        product_loader.add_xpath('name', u'//span[@itemprop="name"]/text()')
        price = hxs.select(u'//form[@id="vCSS_mainform"]//span[@itemprop="price"]/text()').extract()
        price = price[0] if price else u'0'
        product_loader.add_value('price', price)
        product_loader.add_xpath('sku', u'//span[@class="product_code"]/text()')
        product_loader.add_xpath('identifier', u'//span[@class="product_code"]/text()')
        product_loader.add_xpath('category', u'//td[@class="vCSS_breadcrumb_td"]//a[position()=2]/@title')
        product_loader.add_xpath('image_url', u'concat("http://lamusic.ca",//img[@id="product_photo"]/@src)')
        product_loader.add_xpath('brand', u'//meta[@itemprop="manufacturer"]/@content')
        availability_label = ''.join(hxs.select('//b[contains(text(), "Availability:")]/text()').extract()).strip()
        # in_stock = 'IN STOCK' in ''.join(hxs.select('//div[@itemprop="offers"]/text()').extract()).strip().upper()
        # if availability_label and not in_stock:
        #     product_loader.add_value('stock', 0)
        if hxs.select(u'//img[@class="vCSS_img_icon_free_shipping"]'):
            product_loader.add_value('shipping_cost', '0')

        product = product_loader.load_item()
        if hxs.select(u'//tr[@class="Multi-Child_Background"]'):
            for opt in hxs.select(u'//tr[@class="Multi-Child_Background"]'):
                p = Product(product)
                p['sku'] = opt.select(u'./td[1]/text()').extract()[0].strip()
                p['identifier'] = opt.select(u'./td[1]/text()').extract()[0].strip()
                p['name'] = opt.select(u'./td[2]/text()').extract()[0].strip()
                try:
                    p['price'] = opt.select(u'./td[4]//span[@itemprop="price"]/text()').extract()[0].strip().replace('$', '').replace(',', '')
                except:
                    price = opt.select(u'./td[4]//span/text()').extract()
                    if not price:
                        price = opt.select(u'./td[3]//span[contains(text(), "$")]/text()').extract()

                    p['price'] = price[0].strip().replace('$', '').replace(',', '')
                    
                if p.get('identifier') and p.get('price') > 0:
                    yield p
        elif product.get('identifier') and product.get('price') > 0:
            yield product
