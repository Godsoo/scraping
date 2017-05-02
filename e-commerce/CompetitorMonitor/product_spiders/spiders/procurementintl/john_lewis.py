import os
import xlrd

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin
from decimal import Decimal
from scrapy import log
import copy

HERE = os.path.abspath(os.path.dirname(__file__))


class JohnLewisSpider(BaseSpider):
    name = 'procurement_john_lewis'
    start_urls = ['http://www.impro-int.com/']
    allowed_domains    = ['johnlewis.com', 'impro-int.com']

    def start_requests(self):
        country_url = "http://www.johnlewis.com/store/international/ajax/changeCountryAjaxRequest.jsp"
        formdata = {'country': 'GB',
                    'sourceUrl': 'http://www.johnlewis.com/',
                    'switchToggle': 'Change Country Overlay'}
        yield FormRequest(country_url, formdata=formdata, callback=self.parse_country)

    def parse_country(self, response):
        for url in self.start_urls:
            yield Request(url)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        file_path = HERE + '/ProductsToTest.xlsx'
        wb = xlrd.open_workbook(file_path)
        sh = wb.sheet_by_index(0)

        for rownum in xrange(sh.nrows):
            if rownum < 1:
                continue
            row = sh.row_values(rownum)
            url = row[15]
            loader = ProductLoader(item=Product(), selector=Product())
            loader.add_value('identifier', row[0])
            if url:
                yield Request(url, callback=self.parse_product, meta={'product': loader.load_item()})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        product = response.meta.get('product', Product())

        # sub_items = hxs.select('//div[@class="item-details"]//h3/a/@href').extract()
        # if sub_items:
        #     for sub_item in sub_items:
        #         url = urljoin(response.url, sub_item)
        #         yield Request(url, callback=self.parse_product, meta=response.meta)
        #     return

        # option_links = hxs.select('//form[@id="save-product-to-cart"]/section//div/ul[@class="selection-grid"]/li/a/@href').extract()
        # if not response.meta.get('option', False) and option_links:
        #     for link in option_links:
        #         url = urljoin(response.url, link)
        #         meta = response.meta
        #         meta['option'] = True
        #         yield Request(url, meta=meta, dont_filter=True, callback=self.parse_product)
        #     return

        loader = ProductLoader(item=product, response=response)
        loader.add_value('url', response.url)

        #== Extracting Product Name ==#
        name = hxs.select('//div[@id="prod-child"]/div[@id="prod-child-products" and @class="mod mod-child-products"]/h3/text()').extract()
        if not name:
            name = hxs.select('//h1[@id="prod-title"]/span/text()').extract()
        if not name:
            name = hxs.select("//div[@class='mod mod-product-info']/h2/text()").extract()
        if not name:
            name = hxs.select('//h1[@id="prod-title"]/text()').extract()
        if not name:
            name = hxs.select('//h1/span[@itemprop="name"]/text()').extract()
        if name:
            name = name[0].strip()
        else:
            log.msg('### No name at '+ response.url, level=log.INFO)

        tmp = hxs.select('//div[@class="detail-pair"]/p/text()').extract()
        if tmp:
            name += ', ' + tmp[0]
        loader.add_value('name', name)

        #== Extracting Price, Stock & Shipping cost ==#
        price = 0
        stock = 0
        tmp   = hxs.select('//div[@class="basket-fields"]/meta[@itemprop="price"]/@content').extract()
        if not tmp:
            tmp = hxs.select('//div[@class="basket-fields"]//strong[@class="price"]/text()').extract()
        if not tmp:
            tmp = hxs.select('//section[div[@id="prod-product-code"]]//div[@id="prod-price"]/p//strong//text()').extract()
        if not tmp:
            tmp = hxs.select('//div[@id="prod-price"]//span[@itemprop="price"]/text()').extract()
        if tmp:
            price = extract_price(''.join(tmp).strip().replace(',',''))
            stock = 1
            if Decimal(price) < 50.0:
                loader.add_value('shipping_cost', '3.00')
        loader.add_value('price', price)
        loader.add_value('stock', stock)

        #== Extracting Image URL ==#
        tmp = hxs.select('//li[contains(@class,"image")]//img/@src').extract()
        if tmp:
            url = urljoin(response.url, tmp[0])
            loader.add_value('image_url', url)
        

        #== Extracting Brand ==#
        tmp = hxs.select('//div[@itemprop="brand"]/span/text()').extract()
        if tmp:
            loader.add_value('brand', tmp[0].strip())
        

        #== Extracting Category ==#
        tmp = hxs.select('//div[@id="breadcrumbs"]/ol/li/a/text()').extract()
        if len(tmp)>1:
            loader.add_value('category', ' > '.join(tmp[-3:]))

        price = loader.get_output_value('price')
        if price:
            price = Decimal(price)
            if price < 50.0:
                loader.add_value('shipping_cost', '3.00')


        product = loader.load_item()


        #== Extracting Options ==#
        options = hxs.select('//div[@id="prod-multi-product-types"]//div[@itemprop="offers"]')
        if not options:
            yield product
            return

        #== Process options ==#
        for sel in options:
            item = copy.deepcopy(product)
            tmp  = sel.select('.//div[contains(@class,"mod-product-code")]/p/text()').extract()
            if tmp:
                item['identifier'] = "%s_%s" % (item['identifier'],tmp[0])
                item['sku'] = tmp[0]
            tmp = sel.select('.//h3/text()').extract()
            if tmp:
                item['name'] = name + ' - ' + tmp[0]

            price = 0
            tmp = sel.select('.//p[@class="price"]/strong/text()').re('[0-9,.]+')
            if not tmp:
                tmp = sel.select('.//strong[@class="price"]/text()').re('[0-9,.]+')
            if tmp:
                price = extract_price(tmp[0].strip().replace(',',''))
                if Decimal(price) < 50.0:
                    item['shipping_cost'] = '3.00'
                else:
                    del item['shipping_cost']
            item['price'] = price

            tmp = sel.select('.//link[@itemprop="availability"]/@content').extract()
            if tmp and 'in' in tmp[0].lower():
                item['stock'] = 1
            else:
                item['stock'] = 0
