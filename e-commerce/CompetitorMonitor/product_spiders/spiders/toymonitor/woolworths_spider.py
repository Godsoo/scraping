import os
import re
import xlrd
import paramiko

from scrapy import log

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from toymonitoritems import ToyMonitorMeta

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from brands import BrandSelector
HERE = os.path.abspath(os.path.dirname(__file__))

class WoolWorthsSpider(BaseSpider):
    name = 'toymonitor-woolworths.co.uk'
    allowed_domains = ['woolworths.co.uk']
    start_urls = ['http://www.woolworths.co.uk/brand-store.page?end=5132']
    errors = []
    brand_selector = BrandSelector(errors)
    #field_modifiers = {'brand': brand_selector.get_brand}

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        file_path = HERE + '/Brandstomonitor.xlsx'
        wb = xlrd.open_workbook(file_path)
        sh = wb.sheet_by_index(0)

        brands_to_monitor = []
        for rownum in xrange(sh.nrows):
            if rownum < 1:
                continue
            row = sh.row_values(rownum)
            brands_to_monitor.append(re.sub(r'\W+', '', row[0].upper().strip()))

        site_brands = hxs.select('//div[@class="columns"]/ul/li/a')
        for brand in site_brands:
            brand_name = brand.select('text()').extract()[0].split('(')[0].strip()
            brand_url = brand.select('@href').extract()[0]
            if re.sub(r'\W+', '', brand_name.upper()) in brands_to_monitor:
                brand_url = urljoin_rfc(get_base_url(response), brand_url)
                yield Request(brand_url, callback=self.parse_brand, meta={'brand': brand_name})

    def parse_brand(self, response):
        hxs = HtmlXPathSelector(response)

        products = hxs.select('//a[@class="productTitle"]/@href').extract()
        for product in products:
            yield Request(product, callback=self.parse_product, meta=response.meta)

        next = hxs.select('//a[@class="paginationNext"]/@href').extract()
        if next:
            next = urljoin_rfc(get_base_url(response), next[0])
            yield Request(next, callback=self.parse_brand, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        
        loader = ProductLoader(item=Product(), response=response)
        name = ''.join(hxs.select('//h1[@class="productHeading"]//text()').extract())
        loader.add_value('name', name)
        loader.add_value('url', response.url)
        loader.add_value('brand', response.meta.get('brand', ''))
        category = re.findall(u',\\ncategory: "(.*)",', response.body)
        category = category[0] if category else ''
        loader.add_value('category', category)
        loader.add_xpath('sku', '//span[@id="catalogueNumber"]/text()')
        loader.add_xpath('identifier', '//span[@id="catalogueNumber"]/text()')
        image_url = hxs.select('//div[@id="amp-originalImage"]/img/@src').extract()
        if image_url:
            loader.add_value('image_url', image_url[0])

        price = ''.join(hxs.select('//div[@class="priceNow"]//text()').extract())
        loader.add_value('price', price)

        out_of_stock = 'IN STOCK' not in ''.join(hxs.select('//meta[@property="product:availability"]/@content').extract()).upper()
        if out_of_stock:
            loader.add_value('stock', '0')

        item = loader.load_item()
        metadata = ToyMonitorMeta()
        ean = ''.join(hxs.select('//span[@id="productEAN"]/text()').extract()).strip()
        if ean:
            metadata['ean'] = ean
        item['metadata'] = metadata

        yield item
