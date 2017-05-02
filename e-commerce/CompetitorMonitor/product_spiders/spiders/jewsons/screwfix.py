import os

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class ScrewfixSpider(BaseSpider):
    name = 'jewsons-screwfix.com'
    allowed_domains = ['screwfix.com']

    start_urls = ('http://www.screwfix.com',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select(u'//a/@href').extract():
            if 'forceUserMode=UK' in url:
                url = urljoin_rfc(get_base_url(response), url)
                yield Request(url, callback=self.start_search)
                return
        self.log('Force user mode = UK not found!')
        for x in self.start_search(response):
            yield x

    def start_search(self, response):
        for url in (
            # tools category
            'http://www.screwfix.com/c/tools/cat830034',
            # clearance tools
            'http://www.screwfix.com/search.do?fh_search=clearance&fhSearchParams=fh_location%3D%2F%2Fscrewfix%2Fen_GB%2F%24s%3Dclearance%2Fcategories%3C%7Bscrewfix_cat830034%7D%26fh_eds%3D%25C3%259F%26fh_refview%3Dsearch%26fh_reffacet%3Dcategories%26fh_refpath%3Dfacet_87316993&fh_sort_by&cm_sp=Landing_Page-_-Clearance-_-NavTools',):
            yield Request(url, callback=self.parse2)

    def parse2(self, response):
        hxs = HtmlXPathSelector(response)

        subcats = hxs.select('//a[@class="range_links"]/@href').extract()
        subcats += hxs.select('//a[@forsubcatid]/@href').extract()

        for cat in subcats:
            yield Request(urljoin_rfc(get_base_url(response), cat), callback=self.parse2)

        for page in hxs.select("//a[@class='page-link']/@href").extract():
            yield Request(urljoin_rfc(get_base_url(response), page), callback=self.parse2)

        for product in self.parse_products(hxs):
            yield product

    def parse_products(self, hxs):
        products = hxs.select('//div[@class="gallery-product-title"]/..')

        for product in products:
            loader = ProductLoader(selector=product, item=Product())
            loader.add_xpath('name', './/h2/a/text()')
            loader.add_xpath('url', './/h2/a/@href')
            loader.add_xpath('price', './/em[starts-with(@id, "product_list_price")]/text()')
            loader.add_xpath('identifier', './/span/@quotenumberproductid')

            yield loader.load_item()
