import re
import logging
import urllib

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class ClarkeToolingCoUkSpider(BaseSpider):
    name = 'clarketooling.co.uk'
    allowed_domains = ['clarketooling.co.uk']
    start_urls = ('http://www.clarketooling.co.uk',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select(u'//div[@class="wireframemenu"]//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product_list)

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)

        category = hxs.select(u'//p[@class="text_breadcrumbs"]//text()').extract()
        category = [c.replace('>', '').strip() for c in category]
        category = [c for c in category if c][2]

        for url in hxs.select(u'//table[@class="bgmain"]//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product_list)

        for product in hxs.select(u'//td/a/../h2/../../..'):
            product_loader = ProductLoader(item=Product(), selector=product)
            product_loader.add_value('url', response.url)
            #Products with the same name and different prices exist, only Ref differs
            #product_loader.add_xpath('name', u'normalize-space(substring-before(.//h2/text(), "(Ref:"))')
            product_loader.add_xpath('name', u'normalize-space(.//h2/text())')
            product_loader.add_xpath('price', u'.//table//td[1]/span[@class="actlarge"]/text()')
            if not product_loader.get_collected_values('price'):
                product_loader.add_value('price', '')
            product_loader.add_xpath('sku', u'substring(.//h2/../a/@name, 2)')
            sku = product.select(u'substring(.//h2/../a/@name, 2)').extract()[0]
            product_loader.add_value('identifier', sku.lower())
            product_loader.add_value('category', category)
            img = product.select(u'.//td/a/img/@src').extract()
            if img:
                img = urljoin_rfc(get_base_url(response), img[0])
                product_loader.add_value('image_url', img)
            yield product_loader.load_item()
#            product_loader.add_xpath('brand', '')
#            product_loader.add_xpath('shipping_cost', '')

#        next_page = hxs.select(u'//div[@class="CategoryPagination"]/div/a[contains(text(),"Next")]/@href').extract()
#        if next_page:
#            yield Request(next_page[0], callback=self.parse_product_list)
