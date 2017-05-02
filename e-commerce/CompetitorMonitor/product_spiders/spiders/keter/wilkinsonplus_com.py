# -*- coding: utf-8 -*-

from scrapy.selector import HtmlXPathSelector
from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy.utils.response import get_base_url
import urlparse
import urllib
from product_spiders.items import Product,  ProductLoader
from keteritems import KeterMeta

__author__ = 'Theophile R. <rotoudjimaye.theo@gmail.com>'


class WilkinsonPlusSpider(BaseSpider):
    name = "wilkinsonplus.com"
    start_urls = ["http://www.wilkinsonplus.com/"]
    allowed_domains = ['wilkinsonplus.com', 'wilko.com']

    # 2013-12-26 the spider still finds only 14 Keter products and spends more than
    # 3 hours looking for other brands (none found)
    #BRANDS = ['Keter', 'SUNCAST', 'RUBBERMAID', 'LIFETIME', 'STEP 2', 'STERILITE']
    BRANDS = ['Keter']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for brand in self.BRANDS:
            url = urlparse.urljoin(base_url, "search?" + urllib.urlencode({'searchsubmit.x': 0, 'searchsubmit.y': 0, 'q': brand}))

            yield Request(url=url, callback=self.load_products(brand), meta={'brand': brand})

    def load_products(self, brand):

        def parse(response):
            hxs = HtmlXPathSelector(response)
            base_url = get_base_url(response)

            # Search result does not contain all products
            # so we scrape filtering pages from left part of page for more products
            if response.meta['brand'] == 'Keter':
                if not 'filter' in response.meta or not response.meta['filter']:
                    for url in hxs.select("//div[@id='pdxttyperesults']//a/@href").extract():
                        yield Request(urlparse.urljoin(base_url, url), callback=self.load_products(brand), meta={'filter': True, 'brand': response.meta['brand']})

            next_page = hxs.select('//div[@class="pagnLinkNavigate"]//span[@class="pagnNext"]')
            if next_page:
                yield Request(urlparse.urljoin(base_url, next_page.select('.//a/@href').extract()[0]), callback=self.load_products(brand), meta={'brand': response.meta['brand']})

            for product_box in hxs.select('//ul[contains(@class, "prodsGrid")]//form[starts-with(@id,"addproduct")]'):
                product_loader = ProductLoader(item=Product(), selector=product_box)

                url = product_box.select('.//h3/a/@href').extract()[0]
                identifier = url.split('/')[-1]

                product_loader.add_xpath('name', './/h3/a/text()')
                product_loader.add_xpath('image_url', 'div/a/img/@src')
                product_loader.add_value('url',  url)
                product_loader.add_value('identifier',  identifier)
                product_loader.add_xpath('price','.//span[@itemprop="price"]/text()')
                product_loader.add_value('brand', brand.strip().lower())

                product = product_loader.load_item()
                product['metadata'] = KeterMeta()
                product['metadata']['brand'] = brand

                if brand.upper() in product['name'].upper()\
                        or brand in ('Keter', ):
                    yield Request(url=product['url'], callback=self.check_product_category(product))
                else:
                    yield Request(url=product['url'], callback=self.check_product_brand(product, brand))
        return parse

    def check_product_category(self, product):
        def open_product_page(response):
            hxs = HtmlXPathSelector(response)
            base_url = get_base_url(response)        
            product['category'] = hxs.select('//p[@class="crumbtrail"]/a/text()').extract()[-1]
            yield product
        return open_product_page

    def check_product_brand(self, product, brand):
        def open_product_page(response):
            hxs = HtmlXPathSelector(response)
            base_url = get_base_url(response)
            for spec in hxs.select('//div[@class="pdxtfields"]'):
                if "Brand" in spec.select("./p[1]/text()").extract()[0]\
                        and brand.upper() in spec.select("./p[2]/text()").extract()[0].upper():
                    product['category'] = hxs.select('//p[@class="crumbtrail"]/a/text()').extract()[-1]
                    yield product
        return open_product_page
