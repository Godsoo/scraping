import os
import xlrd

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.spider import BaseSpider
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class TescoSpider(BaseSpider):
    name = 'roys-argos.co.uk'
    allowed_domains = ['argos.co.uk']
    start_urls = ['http://www.argos.co.uk']

    def start_requests(self):
        filename = os.path.join(HERE, 'RoysData.xlsx')
        wb = xlrd.open_workbook(filename)
        sh = wb.sheet_by_name('Sheet1')

        for rownum in xrange(sh.nrows):
            if rownum < 1:
                continue

            row = sh.row_values(rownum)
            product_url = row[17]
            if product_url:
                meta = {}
                meta['categories'] = [row[1], row[3], row[5]]
                meta['sku'] = row[6]
                yield Request(product_url, meta=meta)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        meta = response.meta

        url = response.url
        l = ProductLoader(item=Product(), response=response)

        name = hxs.select("//div[@id='pdpProduct']/h1/text()").extract()
        if not name:
            self.log("ERROR! NO NAME! %s" % url)
            log.msg('ERROR! NO NAME!')
            if response.url.endswith('.htm'):
                yield Request(response.url.replace('.htm', '.html'), callback=self.parse_product)
            return
        name = name[0].strip()
        l.add_value('name', name)

        price = hxs.select("//div[@id='pdpPricing']/span[contains(@class, 'actualprice')]/span/text()").extract()
        if not price:
            self.log("ERROR! NO PRICE! %s %s" % (url, name))
            return
        price = "".join(price)

        l.add_value('sku',  meta['sku'])

        for category in meta['categories']:
            l.add_value('category', category)

        product_image = hxs.select('//*[@id="mainimage"]/@src').extract()
        if not product_image:
            self.log('ERROR: no product Image found!')
        else:
            image = urljoin_rfc(get_base_url(response), product_image[0].strip())
            l.add_value('image_url', image)

        l.add_value('url', url)
        l.add_value('price', price)
        l.add_xpath('identifier', u'//form/input[@name="productId"]/@value')
        yield l.load_item()
