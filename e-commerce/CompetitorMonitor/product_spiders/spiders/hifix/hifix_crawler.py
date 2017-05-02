import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector, XmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy import log

from scrapy.contrib.spiders import SitemapSpider

from product_spiders.items import (Product, 
                                   ProductLoaderWithNameStrip as ProductLoader)


class HiFixSpider(BaseSpider):
    name = 'hifix.co.uk'
    allowed_domains = ['www.hifix.co.uk']
    start_urls = ('http://www.hifix.co.uk/',)
    # sitemap_urls = ('http://www.hifix.co.uk/sitemap.xml',)

    '''
    def start_requests(self):
        for url in self.start_urls:
            yield Request(
                url=url,
                callback=self.parse_sitemap,
            )

    def parse_sitemap(self, response):
        namespaces = {
            'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9',
            # 'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
        }
        xxs = XmlXPathSelector(response)
        for namespace, scheme in namespaces.iteritems():
            xxs.register_namespace(namespace, scheme)
        for url in xxs.select("//sitemap:url/sitemap:loc/text()").extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product_list, cookies={}, meta={'dont_merge_cookies': True})
    '''

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        meta = response.meta
        categories = hxs.select('//li[contains(@class,"  mcpdropdown parent  level0 ")]/a/@href')[1:].extract()
        categories += hxs.select('//ul[@class="brands level0"]//a/@href').extract()
        for url in categories:
            meta = {'dont_merge_cookies': True}
            url = urljoin_rfc(base_url, url.strip()) + '?limit=all'
            yield Request(url, cookies={}, meta=meta)

        next_page = hxs.select('//a[@class="next i-next"]/@href').extract()
        if next_page:
            meta = {'dont_merge_cookies': True}
            url = urljoin_rfc(base_url, next_page[0])
            yield Request(next_page[0], cookies={}, meta=meta)

        products = hxs.select('//h2[@class="product-name"]/a/@href').extract()
        for url in products:
            url = urljoin_rfc(base_url, url)
            meta = {'dont_merge_cookies': True}
            yield Request(url, callback=self.parse_product, cookies={}, meta=meta)


    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        brand = hxs.select('//th[@class="label" and text()="Brand"]/following-sibling::td/text()').extract()

        sku = hxs.select('//div[@class="nine columns rightpart omega"]').re('Product code: (.*?)\<')
        if sku:
            sku = sku[0].strip()
        image_url = hxs.select('//img[@id="image"]/@src').extract()
        category = ' > '.join(hxs.select('//div[contains(@class,"breadcrumbs")]/ul/li/a/text()').extract()[1:])

        name = hxs.select('//div[@class="nine columns rightpart omega"]/h1/text()')[0].extract()

        multiple_prices = hxs.select('//select[@class="values"]/option')[1:]
        if not multiple_prices:

            product_loader = ProductLoader(item=Product(), response=response)
            name_parsed = False
            try:
                product_loader.add_value('name', name.strip())
                name_parsed = True
            except:
                pass
            if not name_parsed:
                try:
                    product_loader.add_value('name', name.strip().encode('utf-8'))
                    name_parsed = True
                except:
                    pass
            if not name_parsed:
                try:
                    product_loader.add_value('name', name.strip().decode('utf-8'))
                except:
                    pass
            product_loader.add_value('url', response.url)

            price = hxs.select('//div[@class="nine columns rightpart omega"]//span[@class="price"]/text()').extract()
            if not price:
                price = hxs.select('//div[@class="nine columns rightpart omega"]//p[@class="special-price"]/span[contains(@class,"price product")]/text()').extract()
            product_loader.add_value('price', price)

            product_loader.add_value('image_url', image_url)
            product_loader.add_value('category', category)
            product_loader.add_value('brand', brand)
            product_loader.add_value('sku', sku)
            identifier = hxs.select('//input[@type="hidden" and @name="product"]/@value')[0].extract()
            product_loader.add_value('identifier', identifier)

            yield product_loader.load_item()
        else:
            for option in multiple_prices:
                product_loader = ProductLoader(item=Product(), selector=hxs)
                name_parsed = False
                try:
                    product_loader.add_value('name', u'{} {}'.format(name.strip(), option.select('./text()')[0].extract().strip()))
                    name_parsed = True
                except:
                    pass
                if not name_parsed:
                    try:
                        product_loader.add_value('name', '{} {}'.format(name.strip().encode('utf-8'), option.select('./text()')[0].extract().strip().encode('utf-8')))
                        name_parsed = True
                    except:
                        pass
                if not name_parsed:
                    try:
                        product_loader.add_value('name', u'{} {}'.format(name.strip().decode('utf-8'), option.select('./text()')[0].extract().strip().decode('utf-8')))
                    except:
                        pass
                product_loader.add_value('url', response.url)
                product_loader.add_value('price', option.select('./@price')[0].extract())
                product_loader.add_value('image_url', image_url)
                product_loader.add_value('category', category)
                product_loader.add_value('brand', brand)
                product_loader.add_value('sku', sku)
                product_loader.add_value('identifier', option.select('./@value')[0].extract())

                yield product_loader.load_item()
