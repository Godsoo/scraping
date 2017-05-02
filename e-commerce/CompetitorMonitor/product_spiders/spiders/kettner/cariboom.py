import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)

from utils import extract_price_eu


class CariboomSpider(BaseSpider):

    name = 'cariboom.com'
    allowed_domains = [name]
    start_urls = ('http://www.cariboom.com',)

    categories_xpath = "//div[@id='custommenu']//a/@href"
    categories_nextpage_xpath = None
    products_xpath = "//div[@class='category-products']/ol/li"
    products_nextpage_xpath = "//*[@id='contenu']/div[2]/div[2]/div/ol/li[3]/@onclick"
    products_nextpage_re = "='(.+)'"

    errors = []

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        yield Request('http://www.cariboom.com/catalogsearch/result/?q=%25',
                      callback=self.parse_page)

        '''
        categories = hxs.select(self.categories_xpath).extract()
        for url in categories:
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_page)
        '''


    def parse_page(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        '''
        subcats = hxs.select('//div[@class="child_cat"]/@onclick').re(r'(http.*html)')
        for url in subcats:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_page)
        '''

        pages = hxs.select('//a[contains(@class, "page_page")]/@href').extract()
        for url in pages:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_page)


        for z in hxs.select(self.products_xpath):
            pprice = z.select('./div[@class="prix_sans_promo"]/div[@class="prix_vente_sans_promo"]/text()').extract()
            if not pprice:
                pprice = z.select('./div[@class="prix"]/div[@class="prix_vente"]/text()').extract()
            if not pprice:
                self.errors.append('WARNING: No price in %s' % response.url)
                continue
            else:
                price = pprice[0]
            try:
                product_url = z.select('./div[@class="title"]/h2/a/@href').extract()[0]
            except:
                self.errors.append('WARNING: No url in %s' % response.url)
                continue

            loader = ProductLoader(selector=z, item=Product())
            loader.add_xpath('identifier', './/div[contains(@id, "im_prod_")]/@id', re=r'im_prod_(\d+)')
            loader.add_xpath('name', './div[@class="title"]/h2/a/text()')
            loader.add_value('url', urljoin_rfc(base_url, product_url))
            loader.add_value('price', extract_price_eu(price.replace(' ', '')))

            yield loader.load_item()

