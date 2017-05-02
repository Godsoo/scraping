import csv
import urlparse
import os
import copy
import re
from StringIO import StringIO

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoader
#from bablas_item import ProductLoader


HERE = os.path.abspath(os.path.dirname(__file__))

class ShadeStationSpider(BaseSpider):
    name = 'fashioneyewear-trial-shadestation.co.uk'
    allowed_domains = ['shadestation.co.uk']

    filename = os.path.join(HERE, 'fashioneyeware_products.csv')
    start_urls = ('file://' + filename,)
    
    def parse(self, response):
        rows = csv.DictReader(StringIO(response.body))
        for row in rows:
            if 'shadestation' in row['ShadeStation']:
                url = row['ShadeStation'].strip()
                url = url + ('?' if '?' not in url else '&') + 'currency=GBP'
                yield Request(url, dont_filter=True, callback=self.parse_product, meta={'row':row})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        row = response.meta['row']

        loader = ProductLoader(item=Product(), response=response)
        identifier = hxs.select(u'//div[label[text()="Shade Station code"]]/span/text()').extract()

        if identifier:
            identifier = identifier[0].strip()
        else:
            return

        name = hxs.select(u'//h1[@itemprop="name"]/text()').extract()[0].strip()
        size = ''.join(hxs.select('//div[label/text()="Size"]/span/text()').extract()).strip()
        if size:
            name += ' ' + size
        frame = ''.join(hxs.select('//div[label/text()="Frame"]/span/text()').extract()).strip()
        if frame:
            name += ' ' + frame
        lens = ''.join(hxs.select('//div[label/text()="Lens"]/span/text()').extract()).strip()
        if lens:
            name += ' ' + lens

        category = hxs.select(u'//div[@itemprop="breadcrumb"]/a/text()').extract()
        category = category[-1].strip() if category else ''
        loader.add_value('identifier', identifier)
        loader.add_value('name', name)
        loader.add_value('brand', category)
        loader.add_value('category', category)
        loader.add_value('sku', row['SKU'])
        loader.add_value('url', response.url)
        price = hxs.select(u'//div[@itemprop="price"]/text()').re('Our Price (.*)')
        if not price:
            price = hxs.select(u'//div[@itemprop="price"]/text()').extract()
        price = price[0] if price else '0.00'
        loader.add_value('price', price)
        image = hxs.select(u'//div[@id="product_image_crop"]/div/@imageurl').extract()
        image = image[0] if image else ''
        image = urlparse.urljoin(base_url, image)
        loader.add_value('image_url', image)

        out_of_stock = hxs.select(u'//div[@itemprop="availability"]/text()').re(r'(?i)out of stock')
        if out_of_stock:
            stock = 0
        else:
            stock_availability = hxs.select(u'//div[@class="stockstatus"]/div[@class="actualstatus" and child::*]/text()').extract()
            if not stock_availability:
                stock_availability = hxs.select(u'//div[@class="stockstatus"]/div[@class="sitestatus"]/div[@class="actualstatus" and child::*]/text()').extract()
            if stock_availability:
                stock = hxs.select(u'//div[@class="stockstatus"]/div[@class="furtherdetails"]/text()').re(u'[\d]+')
                if not stock:
                    stock = hxs.select(u'//div[@class="stockstatus"]/div[@class="sitestatus"]/div[@class="furtherdetails"]/text()').re(u'[\d]+')
                stock = int(stock[0])
            else:
                stock = None
        loader.add_value('stock', stock)
        yield loader.load_item()

        subitems = hxs.select('//select[@name="sizeSelector"]/option/@value').extract()

        for url in subitems:
            url = urlparse.urljoin(get_base_url(response), url).replace("#sizeanchor", "")

            yield Request(url, callback=self.parse_product, meta=response.meta)

