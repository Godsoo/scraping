import re
import logging

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoader
from product_spiders.spiders.sagemcom.utils import get_product_list

from product_spiders.utils import url_quote


class ArgosCoUkSagemcomSpider(BaseSpider):
    name = 'argos.co.uk_sagemcom'
    allowed_domains = ['argos.co.uk']
    search_url = 'http://www.argos.co.uk/static/Search/searchTerms/%s.htm'

    def start_requests(self):
        for row in get_product_list('Argos'):
            if row['url']:
                yield Request(row['url'], callback=self.parse_product, meta=row)
            else:
                url = self.search_url % (url_quote(row['search'].pop(0)))
                yield Request(url, callback=self.parse_search, meta=row)

    def get_identifier(self, url):
        reg = r'.*/(.*)\.htm'
        m = re.search(reg, url)
        if not m:
            return None
        identifier = m.group(1)
        return identifier

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        url = response.url

        name = hxs.select("//h1[@class='fn']/text()").extract()
        if not name:
            logging.error("ERROR! NO NAME! %s" % url)
            return
        name = name[0].strip()

        identifier = self.get_identifier(url)
        if not identifier:
            logging.error("ERROR! NO IDENTIFIER! URL: %s. NAME: %s" % (response.url, name))
            return

        price = hxs.select("//div[@id='pdpPricing']/span[contains(@class,'actualprice')]/span/text()").extract()
        if not price:
            logging.error("ERROR! NO PRICE! %s %s" % (url, name))
            return
        price = price[0]

        l = ProductLoader(item=Product(), response=response)
        l.add_value('identifier', identifier)
        l.add_value('name', name)
        l.add_value('url', url)
        l.add_value('price', price)
        l.add_value('sku', response.meta['sku'])
        l.add_value('brand', response.meta['brand'])
        l.add_value('category', response.meta['category'])
        img = hxs.select('//img[@id="mainimage"]/@src').extract()
        if img:
            l.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))
        if hxs.select('//strong/strong[contains(text(),"Available")]'):
            l.add_value('stock', '1')
        else:
            l.add_value('stock', '0')
        l.add_value('shipping_cost', '3.95')
        yield l.load_item()

    def parse_search(self, response):
        URL_BASE = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        if '/Product/' in response.url:
            for x in self.parse_product(response):
                yield x
            return

        found = False
        for url in hxs.select('//div[@id="products"]//dt[@class="title"]/a/@href').extract():
            found = True
            yield Request(url, callback=self.parse_product, meta=response.meta)

        # pages
        page_urls = hxs.select("//div[contains(@class, 'pagination')]//a[@class='button']/@href").extract()
        for url in page_urls:
            url = urljoin_rfc(URL_BASE, url)
            yield Request(url)

        if not found and response.meta['search']:
            url = self.search_url % url_quote(response.meta['search'].pop(0))
            yield Request(url, callback=self.parse_search, meta=response.meta)
