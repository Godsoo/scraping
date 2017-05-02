# -*- coding: utf-8 -*-
import logging

import csv
import os.path
import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.base_spiders.bigsitemethodspider import BigSiteMethodSpider

HERE = os.path.abspath(os.path.dirname(__file__))


class BPMPowesSpider(BigSiteMethodSpider):
    name = 'newbricoman-bpm-power.com'
    allowed_domains = ['bpm-power.com']
    # start_urls = ('http://www.bpm-power.com/it', )
    start_urls = ['http://www.bpm-power.com/it/prodotti_fai_da_te_e_ferramenta.html',
                  'http://www.bpm-power.com/it/prodotti_casa_e_giardino.html']

    website_id = 198

    def __init__(self, *args, **kwargs):
        super(BPMPowesSpider, self).__init__(*args, **kwargs)

        self.rows = []
        self.eans = set()

        with open(os.path.join(HERE, 'bricoman_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.rows.append(row)
                self.eans.add(row['EAN'])

    def parse_full(self, response):
        hxs = HtmlXPathSelector(response)

        pages = hxs.select("//div[@class='pagination_box_elegant barra-menu']//a/@href").extract()
        for page_url in pages:
            url = urljoin_rfc(get_base_url(response), page_url)

            r = Request(url, callback=self.parse_full)
            yield r

        for url in set(hxs.select('//div[@class="productListBreadcrumb"]/a/@href').extract()):
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_full)

        category = hxs.select("//div[@id='breadcrumb']/ul[@class='crumbs']/li[@class='middle'][1]//a/text()").extract()
        if not category:
            category = ['']
        category = category[0].strip()

        products = hxs.select("//div[@class='dep_content']/div[@itemtype]/table/tr[1]")
        next_page = hxs.select("//div[@class='pagination_box_elegant barra-menu']//a[contains(text(), '>')]/@href").extract()

        if len(products) < 10 and next_page:
            self.log('WARNING: too few products in %s' % response.url)
            retry = response.meta.get('retry', 0)
            if retry < 10:
                retry += 1
                self.log('Retrying no. %s => %s' % (retry, response.url))
                yield Request(response.url, callback=self.parse_full, meta={'retry': retry}, dont_filter=True)

        for p in products:
            name = p.select(".//div[@class='productsLineName']//div[@itemprop='name']/strong/text()").extract()[0]
            url = p.select(".//div[@class='productsLineName']//a[@itemprop='url']/@href").extract()[0]
            url = urljoin_rfc(get_base_url(response), url)
            brand = p.select(".//span[@itemprop='manufacturer']//a/text()").extract()
            if brand:
                brand = brand[0].strip()
            else:
                brand = ''
            price = p.select(".//span[@itemprop='price']/text()").extract()[0]
            price = price.replace(".", "").replace(",", ".")

            image_url = urljoin_rfc(get_base_url(response), p.select(".//div[@itemprop='image']//img/@src").extract()[0])

            try:
                sku = p.select(".//span[@itemprop='gtin13']/text()").extract()[0].strip()
            except:
                sku = ''
            if sku in self.eans:
                logging.error("QWE. Found EAN: %s" % sku)
            identifier = p.select(".//span[@itemprop='productID']/text()").extract()[0].strip()

            stock_status = p.select(".//table[@class='productsLineTableOptions']/tr[2]/td//td/div/@title").extract()[0]
            if stock_status == u'Disponibile':
                stock = None
            elif u'non Disponibile' in stock_status:
                stock = 0
            elif u'Ultimi pezzi' in stock_status:
                stock = None
            elif u'Esaurito' in stock_status:
                stock = 0
            else:
                logging.error("ASD. Unknown stock status: %s" % stock_status)
                stock = None

            loader = ProductLoader(item=Product(), selector=hxs)
            loader.add_value('name', name)
            loader.add_value('url', url.replace('www.', ''))
            loader.add_value('category', category)
            loader.add_value('brand', brand)
            loader.add_value('image_url', image_url)
            loader.add_value('sku', sku)
            loader.add_value('identifier', identifier)
            loader.add_value('stock', stock)
            loader.add_value('price', price)

            yield Request(url,
                          callback=self.parse_shipping,
                          meta={'item': loader.load_item()})

    def parse_shipping(self, response):
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=response.meta['item'], selector=hxs)

        try:
            shipping_cost = hxs.select('//table[@id="tblProduct"]//td'
                                       '/span[@class="productOptionsShippingTextPrice"]'
                                       '/text()').extract()[0].strip()
            loader.add_value('shipping_cost', shipping_cost)
        except:
            pass

        yield loader.load_item()

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        
        name = hxs.select('//div[@itemprop="name"]/strong/text()').extract()[0]
        category = hxs.select('//ul[@class="crumbs"]/li/a/text()').extract()[-1]

        price = hxs.select('//span[@itemprop="price"]/text()').extract()
        price = price[0].replace(".", "").replace(",", ".") if price else 0.0

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_value('name', name)
        loader.add_value('url', response.url)
        loader.add_value('category', category)
        loader.add_xpath('brand', '//span[@itemprop="name"]/text()')
        loader.add_xpath('image_url', '//a[@itemprop="image"]/img/@src')
        loader.add_xpath('sku', '//span[@itemprop="gtin13"]/text()')
        loader.add_xpath('identifier', '//span[@itemprop="productID"]/text()')
        loader.add_value('price', price)
        try:
            shipping_cost = hxs.select('//table[@id="tblProduct"]//td'
                                       '/span[@class="productOptionsShippingTextPrice"]'
                                       '/text()').extract()[0].strip()
            loader.add_value('shipping_cost', shipping_cost)
        except:
            pass

        yield loader.load_item()
