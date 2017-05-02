import csv
import os
import copy
import shutil

from scrapy import log
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy.http.cookies import CookieJar

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class HeatAndPlumbSpider(BaseSpider):
    name = 'tapoutlet-heatandplumb.com'
    allowed_domains = ['heatandplumb.com']
    start_urls = ['http://www.heatandplumb.com']

    _products_ = {}

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//div[@class="dropdown_fullwidth"]//ul/li/a/@href').extract()
        for category in categories:
            url = urljoin_rfc(get_base_url(response), category)
            yield Request(url)

        sub_categories = hxs.select('//h2[@class="H2section"]/a/@href').extract()
        for sub_category in sub_categories:
            url = urljoin_rfc(get_base_url(response), sub_category)
            yield Request(url)

        products = hxs.select('//div[@class="ContentAlign"]//table/tr/td[@style="padding-bottom:10px;"]/a[1]/@href').extract()
        for product in products:
            url = urljoin_rfc(get_base_url(response), product)
            yield Request(url, callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        # loader.add_value('sku', response.meta['mpn'])
        mpn = hxs.select('//div[@class="prod_info_container"]/h1/i/text()').extract()
        if not mpn:
            mpn = hxs.select('//li/span[@itemprop="identifier"]/text()').extract()

        image_url = hxs.select('//a[@rel="largeimage1"]/@href').extract()
        if image_url:
            image_url = urljoin_rfc(get_base_url(response), image_url[0])
        else:
            image_url = ''

        mpn = mpn[0].replace(' ', '') if mpn else ''
        options = hxs.select('//table[tr/td[@class="radioPadding"]]/tr')
        end_options = None
        for row in options.extract():
            if 'checkbox_header' in row:
                end_options = options.extract().index(row)
                break

        if not end_options:
            end_options = -1

        for option in options[0:end_options]:
            ref = option.select('td/span/b/text()').extract()
            if ref:
                loader = ProductLoader(item=Product(), response=response)
                ref = ref[0]
                name = option.select('td/span/text()').extract()[-2]
                price = option.select('td/text()').extract()[-1]
                if mpn:
                    loader.add_value('identifier', mpn + '-' + ref)
                else:
                    loader.add_value('identifier', ref)
                loader.add_value('name', ref + name)
                loader.add_value('url', response.url)
                loader.add_value('price', price)
                loader.add_value('sku', mpn)
                loader.add_xpath('brand', '//span[@itemprop="brand"]/text()')
                category = hxs.select('//table[@class="bc"]/tr/td/a/text()').extract()
                category = category[-1] if category else ''
                loader.add_value('category', category)
                loader.add_value('image_url', image_url)
                no_stock = hxs.select('//div[@class="new_product"]/form/div/table/tr/td/table/tr/td/img[contains(@src, "not_aval")]')
                if no_stock:
                    loader.add_value('stock', 0)

                item = loader.load_item()

                # sometimes this site repeats products with small differences between them, but the same
                if item['identifier'] in self._products_:
                    item['name'] = self._products_[item['identifier']]  # Then DuplicateProductPickerPipeline will pick up the lowest price product
                else:
                    self._products_[item['identifier']] = item['name']

                yield item

