import os
import paramiko
from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector
from scrapy.spider import BaseSpider
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
import xlrd
from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
from scrapy.exceptions import DontCloseSpider, CloseSpider

HERE = os.path.abspath(os.path.dirname(__file__))


class LondonGraphicsSpider(BaseSpider):
    name = 'londongraphics.co.uk'
    allowed_domains = ['londongraphics.co.uk']
    start_urls = ('http://www.londongraphics.co.uk',)
    products = dict()

    def __init__(self, *args, **kwargs):
        super(LondonGraphicsSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.process_products, signals.spider_idle)

    def process_products(self, spider):
        if spider.name == self.name:
            if self.products:
                r = Request(
                    self.start_urls[0],
                    dont_filter=True,
                    callback=lambda response: self.process_flat_products()
                )
                self._crawler.engine.crawl(r, self)
                raise DontCloseSpider

    def process_flat_products(self):
        for product in self.products.itervalues():
            yield product
        self.products = dict()

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        # grab products from flat file
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "G67nlc4v"
        username = "london_graphics"
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        files = sftp.listdir_attr()

        file_path = HERE+'/londongraphics.xlsx'
        sftp.get('I-E-UPLOADER.xlsx', file_path)

        wb = xlrd.open_workbook(file_path)
        sh = wb.sheet_by_name('Sheet1')

        for rownum in xrange(sh.nrows):
            if rownum == 0:
                continue
            row = sh.row_values(rownum)
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('identifier', row[0])
            loader.add_value('sku', row[0])
            loader.add_value('name', row[1].decode('utf8'))
            price = 0
            if row[4]:
                price = extract_price(str(row[4]))
            loader.add_value('price', price)
            if row[5]:
                loader.add_value('stock', str(row[5]).split('.')[0])
            else:
                loader.add_value('stock', 0)
            loader.add_value('brand', row[2])
            loader.add_value('category', row[3])
            self.products[row[0]] = loader.load_item()

        # proceed with normal crawl
        for url in hxs.select('//*[@id="leftNav"]//a/@href').extract()[1:]:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        # subcategories
        for url in hxs.select('//h2[@class="product-category"]/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_category)

        # products
        for url in hxs.select('//h2[@class="productName"]/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_product,
                          cookies={},
                          meta={'dont_merge_cookies': True})

        # pagination
        for url in hxs.select('//*[@id="ctl00_ContentPlaceHolder1_lblpages"]/a[contains(text(), "Next")]/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_category)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        image_url = hxs.select('//*[@id="zoom1"]/img/@src').extract()
        if not image_url:
            image_url = hxs.select('//div[@class="photo-surround"]/img/@src').extract()
        product_identifier = hxs.select('//*[@id="ctl00_lblbreadcrumbs"]/span/text()').extract()[0].strip()
        product_name = hxs.select('//div[@class="product-title-container"]/h1/text()').extract()[0].strip()
        price = hxs.select('//div[@class="product-price-container"]//span[@class="price"]/text()').extract()[0]
        price = extract_price(price)
        category = hxs.select('//*[@id="ctl00_lblbreadcrumbs"]/a/text()').extract()
        if product_identifier in self.products:
            brand = self.products[product_identifier]['brand']
        else:
            brand = ''
        stock = ''.join(hxs.select('//*[@id="ctl00_ContentPlaceHolder1_dvStock"]/text()').extract())
        shipping = hxs.select('//div[@class="product-delivery-container"]/text()[1]').extract()

        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('identifier', product_identifier)
        product_loader.add_value('name', product_name)
        if image_url:
            product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        product_loader.add_value('sku', product_identifier)
        product_loader.add_value('price', price)
        product_loader.add_value('url', response.url)
        product_loader.add_value('category', category)
        product_loader.add_value('brand', brand)
        if 'Out of Stock' in stock:
            product_loader.add_value('stock', 0)
        if shipping and u'\xa3' in shipping[0]:
            shipping = shipping[0].split(u'\xa3')[1]
            product_loader.add_value('shipping_cost', shipping)
        product = product_loader.load_item()
        self.products.pop(product_identifier, None)
        yield product
