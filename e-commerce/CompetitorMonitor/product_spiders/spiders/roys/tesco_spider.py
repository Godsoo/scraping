import os
import xlrd

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.spider import BaseSpider
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class TescoSpider(BaseSpider):
    name = 'roys-tesco.com'
    allowed_domains = ['tesco.com']
    start_urls = ['http://www.tesco.com']

    def start_requests(self):
        filename = os.path.join(HERE, 'RoysData.xlsx')
        wb = xlrd.open_workbook(filename)
        sh = wb.sheet_by_name('Sheet1')

        for rownum in xrange(sh.nrows):
            if rownum < 1:
                continue

            row = sh.row_values(rownum)
            product_url = row[15]
            if product_url:
                meta = {}
                meta['categories'] = [row[1], row[3], row[5]]
                meta['top_right_price'] = True if row[16].upper() == 'TAKE FROM TOP RIGHT' else False
                meta['sku'] = row[6]
                yield Request(product_url, meta=meta)

    def parse(self, response):
        meta = response.meta
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)
        identifier = hxs.select('//div[@id="productWrapper"]/div[@data-product-id]/@data-product-id').extract()
        loader.add_value('identifier', identifier[0])
        loader.add_xpath('name', '//div[@class="desc"]/h1/span/text()')

        not_available = 'currently not available' in ''.join(hxs.select('//p[@class="warning unavailableMsg"]/strong/text()').extract()).lower()

        if not_available:
            price = 0
        else:
            if meta['top_right_price']:
                price = hxs.select('//div[@id="productWrapper"]//p[@class="price"]/span[@class="linePriceAbbr"]/text()').re(r'\xa3(.*)/')
            else:
                price = hxs.select('//p[@class="price"]/span[@class="linePrice"]/text()').extract()
            price = price[0] if price else 0
        
        loader.add_value('price', price)

        loader.add_value('sku', meta['sku'])
        loader.add_value('url', response.url)
        for category in meta['categories']:
            loader.add_value('category', category)

        image_url = hxs.select('//div[@class="productImage"]/a/img/@src').extract()
        if not image_url:
            image_url = hxs.select('//a[contains(@class, "largeImage")]/img/@src').extract()
        
        imgae_url = image_url[0] if image_url else ''
        loader.add_value('image_url', image_url)

        yield loader.load_item()
