import csv
import os
import copy

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy.http.cookies import CookieJar
from scrapy.utils.response import open_in_browser

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

from decimal import Decimal
from utils import extract_price

CATEGORIES = {'ferramenta': 'FERRAMENTA', 'accessori-auto-moto-bici': 'ACCESSORI AUTO-MOTO-BICI',
              'idrotermosanitari': 'IDROTERMOSANITARI', 'edilizia': 'EDILIZIA',
              'casa': 'CASA', 'giardinaggio': 'GIARDINAGGIO', 'elettricita-illumin': 'ELETTRICITA\' ILLUMIN',
              'legno': 'LEGNO', 'colore-e-docorazione': 'COLORE E DECORAZIONE', 'tempo-libero': 'TEMPO LIBERO',
              'scuola': 'SCUOLA', 'animaleria': 'ANIMALERIA'}

class EdomusSpider(BaseSpider):
    name = 'newbricoman-edomus.eu'
    allowed_domains = ['edomus.eu']
    start_urls = ('http://www.edomus.eu/prodotti/by,product_name/results,11-10.html?filter_product=',)

    '''
    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        categories = hxs.select('//aside[@id="sidebar-a"]//dt[starts-with(@class, "level1")]/span/span/a/@href').extract()[1:]
        for cat in categories:

            yield Request(urljoin_rfc(base_url, cat), callback=self.parse_category)
    '''

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        pages = hxs.select('//div[@id="bottom-pagination"]//a/@href').extract()
        # pages += hxs.select('//a[@id="FWcategorynamelink"]/@href').extract()
        for page in pages:
            yield Request(urljoin_rfc(base_url, page))

        if not pages:
            # Retry
            retry = int(response.meta.get('retry', 0)) + 1
            if retry < 10:
                self.log('>>> Retrying %s No. %s' % (response.url, retry))
                meta = response.meta.copy()
                meta['retry'] = retry
                yield Request(response.url,
                              meta=meta,
                              dont_filter=True)

        for p in self.parse_products(base_url, response, hxs):
            yield p

    def parse_products(self, base_url, response, hxs):
        products = hxs.select('//div[@id="ListView"]/div')

        for r in products:
            try:
                price = r.select('.//span[@class="PricesalesPrice"]/text()').extract()[0]
            except:
                # No price => continue
                continue
            loader = ProductLoader(item=Product(), selector=r)
            loader.add_xpath('name', './/div[@class="FlexibleListBrowseV1ProductName"]/a/text()')
            url = r.select('.//div[@class="FlexibleListBrowseV1ProductName"]/a/@href').extract()[0]
            url = urljoin_rfc(base_url, url)
            loader.add_value('url', url)
            price = price.replace('.', '').replace(',', '.')
            loader.add_value('price', price)
            sku = r.select('.//div[@class="FlexibleCategoryProductSKUListView"]/text()').extract()[0]
            loader.add_value('sku', sku.replace('SKU: ', ''))
            category = url.split('/')[3]
            if category in CATEGORIES:
                category = CATEGORIES[category]
            else:
                category = ''
            loader.add_value('category', category)
            brand = ''.join(r.select('.//div[@class="FlexibleListViewMiddle"]/text()').extract()).strip()
            loader.add_value('brand', brand)
            img_url = r.select('.//img[@class="browseProductImage"]/@src').extract()[0]
            loader.add_value('image_url', urljoin_rfc(base_url, img_url))
            loader.add_xpath('identifier', './/input[@name="virtuemart_product_id[]"]/@value')

            price = extract_price(price)

            if price < Decimal(50):
                loader.add_value('shipping_cost', '7.00')

            yield loader.load_item()
