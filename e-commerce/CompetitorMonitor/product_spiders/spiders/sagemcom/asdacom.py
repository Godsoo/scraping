import logging

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoader
from utils import get_product_list

from product_spiders.utils import url_quote

class AsdaComSpider(BaseSpider):
    name = 'asda.com'
    allowed_domains = ['asda.com']
    start_urls = (
        'http://direct.asda.com/',
        )
    search_url = 'http://direct.asda.com/on/demandware.store/Sites-ASDA-Site/default/Search-Show?q='

    def parse(self, response):
        for row in get_product_list('Asda'):
            if row['url']:
                yield Request(row['url'], callback=self.parse_product, meta=row)
            else:
                url = self.search_url + url_quote(row['search'].pop(0))
                yield Request(url, callback=self.parse_search, meta=row)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        url = response.url

        name = hxs.select("//h1/text()").extract()
        if not name:
            logging.error("ERROR! NO NAME! %s" % url)
            return
        name = name[0]

        price = hxs.select("//div[@id='productDetail']/form/fieldset/div[@class='price']/span[@class='productPrice']/\
                              span[@class='pounds']/text()").extract()
        if not price:
            price = hxs.select("//div[@id='productDetail']/form/fieldset/div[@class='price']/span[@class='productPrice']/\
                              span[@class='newPrice']/text()").extract()
            if not price:
                logging.error("ERROR! NO PRICE! %s %s" % (url, name))
                return
        price = "".join(price)

        l = ProductLoader(item=Product(), response=response)
        l.add_value('identifier', name)
        l.add_value('name', name)
        l.add_value('url', url)
        l.add_value('price', price)
        l.add_value('sku', response.meta['sku'])
        l.add_value('brand', response.meta['brand'])
        l.add_value('category', response.meta['category'])
        img = hxs.select('//a[@class="productImageLink"]/@href').extract()
        if img:
            l.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))
        if hxs.select('//span[@class="stockOK"]'):
            l.add_value('stock', '1')
        else:
            l.add_value('stock', '0')
        l.add_value('shipping_cost', '2.95')
        yield l.load_item()

    def parse_search(self, response):
        hxs = HtmlXPathSelector(response)

        # parse pages
        pages = hxs.select("//div[@class='searchBarPaging']/ul/li/a/@href").extract()
        for page in pages:
            request = Request(page, callback=self.parse_search, meta=response.meta)
            yield request

        # parse products
        found = False
        for url in hxs.select("//div[@id='primary']//div[@class='listItemInnerMost']/div[@class='prodMiniTop']/h4/a/@href").extract():
            found = True
            yield Request(url, callback=self.parse_product, meta=response.meta)

        if not found and response.meta['search']:
            url = self.search_url + url_quote(response.meta['search'].pop(0))
            yield Request(url, callback=self.parse_search, meta=response.meta)
