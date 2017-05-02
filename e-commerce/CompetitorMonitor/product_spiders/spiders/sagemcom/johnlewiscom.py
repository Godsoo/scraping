__author__ = 'juraseg'

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request

from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoader

import logging
from utils import get_product_list


class JohnlewisComSpider(BaseSpider):
    name = 'johnlewis.com'
    allowed_domains = ['johnlewis.com']
    search_url = 'http://www.johnlewis.com/Search/Search.aspx?SearchTerm='

    def start_requests(self):
        for row in get_product_list('John Lewis'):
            if row['url']:
                yield Request(row['url'], callback=self.parse_product, meta=row)
            else:
                url = self.search_url + row['search'].pop(0).replace(' ', '+')
                yield Request(url, callback=self.parse_search, meta=row)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        url = response.url

        name = hxs.select('normalize-space(//*[@itemprop="name"]/text())').extract()

        if not name:
            logging.error("ERROR! NO NAME! %s" % url)
            return
        name = name[0].strip()

        price = hxs.select(
                "//div[@id='prod-price']/p[@class='price']/strong/text()"
                ).extract()
        if not price:
            logging.error("ERROR! NO PRICE! %s %s" % (url, name))
            return
        price = price[0].strip()

        l = ProductLoader(item=Product(), response=response)
        l.add_value('identifier', name)
        l.add_value('name', name)
        l.add_value('url', url)
        l.add_value('price', price)
        l.add_value('sku', response.meta['sku'])
        l.add_value('brand', response.meta['brand'])
        l.add_value('category', response.meta['category'])
        img = hxs.select('//div[contains(@class,"media-images")]//img/@src').extract()
        if img:
            l.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))
        if hxs.select('//div[@data-jl-stock and not(@data-jl-stock="stock")]/@data-jl-stock'):
            l.add_xpath('stock', '//div[@data-jl-stock]/@data-jl-stock')
        else:
            l.add_value('stock', '0')
        l.add_value('shipping_cost', '0')
        yield l.load_item()

    def parse_search(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        # parse pages
        pages = hxs.select("//div[@class='pagenum']/a/@href").extract()
        for page in pages:
            yield Request(
                    url=urljoin_rfc(base_url, page),
                    callback=self.parse_search)

        # parse products
        found = False
        for url in hxs.select("//a[@class='product-link']/@href").extract():
            found = True
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta=response.meta)

        if not found and response.meta['search']:
            url = self.search_url + response.meta['search'].pop(0).replace(' ', '+')
            yield Request(url, callback=self.parse_search, meta=response.meta)
