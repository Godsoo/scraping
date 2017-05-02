__author__ = 'juraseg'

from scrapy import log
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request

from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price

import logging


class PlayComSpider(BaseSpider):
    name = 'play.com'
    allowed_domains = ['play.com']
    start_urls = (
        'http://play.com/',
        )
    search_url = 'http://www.play.com/Search.html?searchtype=allproducts&searchsource=0&cur=257&searchstring='

    keywords = ['Sagemcom', 'Sagem']

    products = [
        'http://www.play.com/Electronics/Electronics/4-/20951407/Humax-HDR-FOX-T2-1TB-Twin-Freeview-HD-Tuner/Product.html?searchstring=Humax+HDR-+FOX+500GB+T2&searchsource=0&searchtype=allproducts&urlrefer=search&cur=257',
        'http://www.play.com/Electronics/Electronics/4-/22057015/Samsung-SMT-S7800-Freesat-HD-PVR/Product.html?searchstring=Samsung+SMT+S7800+Freesat+500GB&searchsource=0&searchtype=allproducts&urlrefer=search&cur=257',
        'http://www.play.com/Electronics/Electronics/4-/18640736/Sony-HDT500-500GB-Freeview-plus-HD-PVR-Digital-TV-Recorder/Product.html?searchstring=sony+hdt500&searchsource=0&searchtype=allproducts&urlrefer=search&cur=257',
        'http://www.play.com/Electronics/Electronics/4-/12538188/Sagemcom-DS186-HD-Satellite-HD-Digital-Freesat-Box/Product.html?searchstring=sagemcom&searchsource=0&searchtype=allproducts&urlrefer=search&cur=257',
        'http://www.play.com/Electronics/Electronics/4-/6433506/Humax-PVR-9300T-320GB-Twin-Tuner-Hard-Disk-Recorder/Product.html?searchstring=humax&searchsource=0&searchtype=allproducts&urlrefer=search&cur=257',
        'http://www.play.com/Electronics/Electronics/4-/19666726/Philips-PICO-Pix-PPX1230-Projector/Product.html',
        'http://www.play.com/Electronics/Electronics/-/3103/2370/-/18531043/Philips-Pico-Micro-Projector-SVGA-20-ANSI-Lumens-USB-Ref-PPX1020/Product.html',
        'http://www.play.com/Electronics/Electronics/4-/24111045/Optoma-PK120-Pocket-PICO-DLP-Projector/Product.html',
        'http://www.play.com/Electronics/Electronics/4-/8114690/Optoma-Pico-DLP-Pocket-Projector/Product.html?searchstring=DLP+pocket+projector&searchsource=0&searchtype=allproducts&urlrefer=search',
        ]

    def start_requests(self):
        for keyword in self.keywords:
            url = self.search_url + keyword
            request = Request(url, callback=self.parse_search)
            yield request

        for url in self.products:
            yield Request(url, callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        url = response.url

        name = hxs.select("//h1/text()").extract()
        if not name:
            logging.error("ERROR! NO NAME! %s" % url)
            return
        name = name[0]

        price = extract_price(''.join(hxs.select("//div[contains(@class,'unit')]//span[contains(@class, 'price')]//text()").extract()))

        l = ProductLoader(item=Product(), response=response)
        l.add_value('identifier', name)
        l.add_value('name', name)
        l.add_value('url', url)
        l.add_value('price', price)
        l.add_value('sku', response.meta.get('sku'))
        l.add_value('category', response.meta.get('category'))
        img = hxs.select('//a[@id="main_product"]/img/@src').extract()
        if img:
            l.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))
        l.add_value('brand', name.split()[0])
        if hxs.select('//p[contains(@class,"in-stock")]/span[contains(text(),"In stock")]'):
            l.add_value('stock', '1')
        else:
            l.add_value('stock', '0')
        if hxs.select('//span[contains(text(),"Free delivery")]'):
            l.add_value('shipping_cost', '0')

        yield l.load_item()

    def parse_search(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        # parse products
        for url in hxs.select("//p[contains(@class, 'media-title')]/a/@href").extract():
            url = urljoin_rfc(base_url, url)
            yield Request(url, callback=self.parse_product, meta=response.meta)

        # parse pages
        pages = hxs.select("//ul[@class='paging']/li/a/@href").extract()
        for page in pages:
            request = Request(urljoin_rfc(base_url, page), callback=self.parse_search)
            yield request


