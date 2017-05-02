# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.contrib.loader import ItemLoader
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
import re, time

from selenium import webdriver
from product_spiders.phantomjs import PhantomJS
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals


class VaudauxSpider(BaseSpider):

    name = "husqvarna-vaudaux.fr"
    allowed_domains = ["vaudaux.fr"]
    start_urls = ["http://www.vaudaux.fr"]

    download_delay = 5


    def parse(self, response):

        hxs = HtmlXPathSelector(response=response)
        base_url = get_base_url(response)

        categories = hxs.select('//div[@id="menu"]//a/@href').extract()
        for url in categories:
            yield Request(urljoin_rfc(base_url, url))

        products = hxs.select('//div[@class="boxListDesc"]/a[h2]/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)


    def parse_product(self, response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        brand = hxs.select('//div[@class="boxDet"]/div[@class="boxDetDesc"]/img/@alt').extract()
        brand = brand[0] if brand else ''
        
        try:
            name = hxs.select('//div[@class="boxDet"]/div[@class="boxDetDesc"]/h1/text()').extract()[0]
        except:
            retries = response.meta.get('retries', 0) + 1
            if retries < 10:
                yield Request(response.url, dont_filter=True, callback=self.parse_product, meta={'retries': retries})
                return
        sku = hxs.select('//div[@class="boxDet"]/div[@class="boxDetDesc"]/h3/text()').extract()
        if sku:
            sku = sku[0]
        else:
            return
        try:
            price = hxs.select('//div[@class="boxDet"]/div[@class="boxDetDesc"]/p[@class="pdtPx"]/text()').extract()[0].replace(' ', '')
        except:
            price = 0
        stock = hxs.select('//a[@class="plusPanier"]').extract()

        image_url = hxs.select('//div[@class="boxDetVisu"]/a/img/@src').extract()
        category = hxs.select('//p[@id="breadcrumb"]/a/text()').extract()


        l = ProductLoader(item=Product(), response=response)
        l.add_value('name', name)
        if image_url:
            l.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        l.add_value('url', response.url)
        l.add_value('price', price)
        l.add_value('brand', brand)
        l.add_value('identifier', sku)
        l.add_value('sku', sku)
        l.add_value('category', category)
        if not stock:
            l.add_value('stock', 0)

        yield l.load_item()

        new_codes = hxs.select("//select[@id='pro_lie']/option[not(contains(@value,'null'))]/@value").extract()
        if new_codes and not response.meta.get('is_option', False):
            for new_code in new_codes:
                formdata = {'action_produit': 'details_ajax', 'id_produit': new_code}
                url = 'http://www.vaudaux.fr/controleur/cProduit.php'
                yield FormRequest(url, dont_filter=True,formdata=formdata, callback=self.parse_ajax_option)

    def parse_ajax_option(self, response):
        base_url = 'http://www.vaudaux.fr'

        option_url = urljoin_rfc(base_url, response.body)
        yield Request(option_url, callback=self.parse_product, meta={'is_option': True})
        

