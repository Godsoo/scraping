import os
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin as urljoin_rfc
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy import log

HERE = os.path.abspath(os.path.dirname(__file__))


class RDGToolsSpider(BaseSpider):
    name = 'rdgtools.co.uk'
    allowed_domains = ['rdgtools.co.uk', 'www.rdgtools.co.uk']
    start_urls = (u'http://www.rdgtools.co.uk/',)

    def _start_requests(self):
        yield Request('http://www.rdgtools.co.uk/acatalog/Proxxon-Drilling---Grinding-Bits.html',
                      callback=self.parse_product)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        parsed_ids = []

        cats = hxs.select('//*[@id="sidebar"]//li[@class="sections-list"]/a/@href').extract()
        if cats:
            for cat in cats:
                yield Request(
                    url=urljoin_rfc(base_url, cat)
                )

        subcats = hxs.select('//*[@id="ContentPage"]//span[@class="boxheading"]/a/@href').extract()
        if subcats:
            for subcat in subcats:
                yield Request(
                    url=urljoin_rfc(base_url, subcat)
                )

        for url in hxs.select('//div[@id="content"]//form//a[@class="read-more"]/@href').extract():
            if url:
                try:
                    pid = url.split('.')[-2].split('-')[-1]
                    if pid not in parsed_ids:
                        parsed_ids.append(pid)
                    yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)
                except:
                    pass

        for url in hxs.select('//div[@id="content"]//form//h1/../../a/@href').extract():
            if url:
                try:
                    pid = url.split('.')[-2].split('-')[-1]
                    if pid not in parsed_ids:
                        parsed_ids.append(pid)
                    yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)
                except:
                    pass

        category = hxs.select('//*[@id="ContentPage"]/p[@class="text_breadcrumbs"]/a/text()').extract()[1:]

        for product in hxs.select('//*[@id="ContentPage"]//div[@class="col-xs-12"]'):
            pid = product.select('.//input[contains(@name, "Q_")]/@name').re(r'Q_(.+)')
            if pid:
                pid = pid[0]
                if pid not in parsed_ids:
                    parsed_ids.append(pid)
                    name = ''.join(product.select('.//h1//text()').extract())
                    url = response.url
                    image_url = product.select('.//img[@class="catalog-image"]/@src').extract()
                    image_url = urljoin_rfc(base_url, image_url[0]) if image_url else ''
                    price = product.select('.//span[@class="catalog-price" or @class="product-price"]/text()').re(u'\xa3([\d\.,]+)')
                    price = price[0]
                    loader = ProductLoader(item=Product(), selector=product)
                    loader.add_value('url', url)
                    loader.add_value('name', name)
                    loader.add_value('sku', pid)
                    loader.add_value('identifier', pid)
                    loader.add_value('category', category)
                    loader.add_value('image_url', image_url)
                    loader.add_value('price', price)
                    yield loader.load_item()

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        category = hxs.select('//*[@id="idBreadcrumbsTop"]/p[@class="text_breadcrumbs"]/a/text()').extract()[1:]

        url = response.url
        try:
            sku = hxs.select('//input[contains(@name, "Q_")]/@name').re(r'Q_(.+)')[0]

        except Exception, e:
            self.log('NO SKU %s' % url)

            return

        names = hxs.select(u'//div[@id="product-page-body"]//h1/text()').extract()
        name = ' '.join(names)

        try:
            image_url = hxs.select(u'//div[@id="product-page-body"]//img[@class="img-responsive catalog-image"]/@src').extract()[0]
            image_url = urljoin_rfc(base_url, image_url)
        except:
            image_url = u''

        price = hxs.select('//div[@id="product-page-body"]//span[@class="catalog-price"]/text()').re(u'\xa3([\d\.,]+)')
        if not price:
            price = hxs.select('//div[@id="product-page-body"]//span[@class="product-price"]/text()').re(u'\xa3([\d\.,]+)')
        try:
            price = price[0]
        except:
            log.msg(">>> WARNING!!! NO PRICE >>> %s >>> %s" % (name, url))
            price = 0

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_value('url', url)
        loader.add_value('name', name)
        loader.add_value('sku', sku)
        loader.add_value('identifier', sku)
        loader.add_value('category', category)
        loader.add_value('image_url', image_url)
        loader.add_value('price', price)
        yield loader.load_item()
