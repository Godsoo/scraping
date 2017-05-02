from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest, HtmlResponse
from scrapy.utils.response import get_base_url
from urllib import urlencode

from product_spiders.base_spiders import PrimarySpider
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price
from scrapy import log
from scrapy.shell import inspect_response

from urlparse import urljoin

import json
import copy

from scrapy.item import Item, Field


class YMeta(Item):
    promotions = Field()

class DebenhamsSpider(PrimarySpider):
    name = 'debenhams'
    #download_delay = 3
    allowed_domains = ['debenhams.com']
    start_urls = ['http://www.debenhams.com/']

    #cookie_num = 0
    #brands = []
    id_seen = []

    csv_file = 'lakeland_debenhams_as_prim.csv'

    def parse(self, response):
        #inspect_response(response, self)
        #yield Request('http://www.debenhams.com/home/cookware/pots-pans', callback=self.parse_products_list)
        #yield Request('http://www.debenhams.com/webapp/wcs/stores/servlet/prod_10701_10001_332056000180TE41_-1', callback=self.parse_product)
        #return

        yield Request('http://www.debenhamsflowers.com/flowers/shop-by-range/all-flowers', callback=self.parse_fl_products_list)
        #return ###
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        links = [
            #'http://www.debenhams.com/gifts/flowers',
            'http://www.debenhams.com/gifts/food-drink-gifts',
            'http://www.debenhams.com/furniture/office-furniture-storage',
            'http://www.debenhams.com/furniture/storage',
        ]
        # Home
        links += hxs.select('//div[text()="Kitchen & cooking"]/following-sibling::ul[1]/li/a/@href').extract()
        links += hxs.select('//div[text()="Small appliances"]/following-sibling::ul[1]/li/a/@href').extract()
        links += hxs.select('//div[text()="Dining"]/following-sibling::ul[1]/li/a/@href').extract()
        links += hxs.select('//div[text()="Soft furnishings"]/following-sibling::ul[1]/li/a/@href').extract()
        links += hxs.select('//div[text()="Garden"]/following-sibling::ul[1]/li/a/@href').extract()
        # Electricals
        links += hxs.select('//div[text()="Household appliances"]/following-sibling::ul[1]/li/a/@href').extract()

        for link in links: ###
            url = urljoin(base_url, link)
            yield Request(url, callback=self.parse_products_list)

    def parse_products_list(self, response):
        #inspect_response(response, self)
        #return
        hxs = HtmlXPathSelector(response)

        links = hxs.select('//div[@id="galleryDisplay"]//td[@class="item"]//a[1]/@href').extract()
        if links:
            #Crawling sub-categories page
            for link in links: ###
                url = urljoin(response.url, link)
                yield Request(url, callback=self.parse_products_list)
            return

        links = hxs.select('//div[@id="body_content_ProductSelectionPage"]//input[@id="productTileImageUrl"]/@value').extract()
        for link in links: ###
            url = urljoin(response.url, link)
            yield Request(url, callback=self.parse_product)

        #To crawl next page.
        #return ###
        tmp = hxs.select('//div[@id="pagination"]/a[text()="Next"]/@href').extract()
        if tmp:
            url = urljoin(response.url, tmp[0])
            yield Request(url, callback=self.parse_products_list)

    def parse_product(self, response):
        #inspect_response(response, self)
        #return
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        tmp = hxs.select('//div[@id="product-item-no"]/p/text()').extract()
        if not tmp:
            tmp = hxs.select('//meta[@property="product_number"]/@content').extract()
        if tmp:
            loader.add_value('identifier', tmp[0].replace('Item No.',''))
            loader.add_value('sku', tmp[0].replace('Item No.',''))
        else:
            log.msg('### No product ID at '+response.url, level=log.INFO)
            return
        #tmp = hxs.select('//input[@name="/atg/store/order/purchase/CartFormHandler.productId"]/@value').extract()
        #if tmp:
        #    loader.add_value('sku', tmp[0])
        name = ''
        tmp = hxs.select('//h1[@class="catalog_link"]/span[@itemprop="name"]/text()').extract()
        if tmp:
            name = tmp[0].strip()
            loader.add_value('name', name)
        else:
            log.msg('### No name at '+response.url, level=log.INFO)
        #price
        price = 0
        stock = 0
        tmp = hxs.select('//div[@itemprop="offers"]/span[@itemprop="price"]/text()').extract()
        if tmp:
            price = extract_price(tmp[0].strip().replace(',',''))
            loader.add_value('price', price)
            stock = 1
        #stock
        #tmp = hxs.select('//form[@id="save-product-to-cart"]//p[not(contains(@class,"hidden"))]/strong[text()="Out of stock"]')
        #if tmp:
        #    stock = 0
        loader.add_value('stock', stock)
        #image_url
        tmp = hxs.select('//div[@id="image_viewer"]//img/@src').extract()
        if tmp:
            url = urljoin(response.url, tmp[0])
            loader.add_value('image_url', url)
        #brand
        tmp = hxs.select('//h1[@class="catalog_link"]/span[@itemprop="brand"]/text()').extract()
        if tmp:
            loader.add_value('brand', tmp[0].strip())
        #category
        tmp = hxs.select('//div[@class="breadcrumb_links" and not(@id)]//a/text()').extract()
        if len(tmp)>3:
            tmp = tmp[-3:]
        if tmp:
            for s in tmp:
                loader.add_value('category', s.strip())
        #shipping_cost
        if price<30:
            loader.add_value('shipping_cost', 3.49)

        product = loader.load_item()

        metadata = YMeta()
        tmp = hxs.select('//p[@class="price-off-and-save"]//text()').extract()
        if tmp:
            metadata['promotions'] = ' '.join([s.strip() for s in tmp if s.strip()])
        product['metadata'] = metadata

        options = None
        tmp = hxs.select('//div[contains(@id,"entitledItem_")]/text()').extract()
        if tmp:
            j = json.loads(tmp[0].replace("'",'"'))
            if j:
                options = j
        #process options
        if options:
            for opt in options: ###
                item = copy.deepcopy(product)
                tmp = opt.get('catentry_id', None)
                if tmp:
                    item['identifier'] += '-' + tmp
                tmp = opt.get('Attributes', None)
                if tmp:
                    item['name'] = name + ' - ' + '-'.join([s for s in tmp.keys()])
                tmp = opt.get('offer_price', None)
                if tmp:
                    price = extract_price(tmp.replace('Now','').strip().replace(',',''))
                    item['price'] = price
                    item['stock'] = 1
                tmp = opt.get('inventory_status', None)
                if tmp and tmp=='Unavailable':
                    item['stock'] = 0

                if not item.get('identifier', None):
                    log.msg('### No product ID at '+response.url, level=log.INFO)
                else:
                    if not item['identifier'] in self.id_seen:
                        self.id_seen.append(item['identifier'])
                        yield item
                    else:
                        log.msg('### Duplicate product ID at '+response.url, level=log.INFO)
            return

        #no options
        if not product.get('identifier', None):
            log.msg('### No product ID at '+response.url, level=log.INFO)
        else:
            if not product['identifier'] in self.id_seen:
                self.id_seen.append(product['identifier'])
                yield product
            else:
                log.msg('### Duplicate product ID at '+response.url, level=log.INFO)

#    def parse_flowers(self, response):
        #inspect_response(response, self)
        #yield Request('http://www.debenhams.com/home/cookware/pots-pans', callback=self.parse_products_list)
        #yield Request('http://www.johnlewis.com/missprint-garden-city-table-linen-accessories/p89014118', callback=self.parse_product)
        #return

        #yield Request('http://www.debenhamsflowers.com/designer-flowers', callback=self.parse_fl_products_list)
        #yield Request('http://www.debenhamsflowers.com/luxury-flowers', callback=self.parse_fl_products_list)

        #hxs = HtmlXPathSelector(response)
        #links = hxs.select('//div[@class="hpcontentborder"]//a[@title and strong]/@href').extract()
        #for link in links[0:1]: ###
        #    url = urljoin(response.url, link)
        #    yield Request(url, callback=self.parse_fl_products_list)

    def parse_fl_products_list(self, response):
        #inspect_response(response, self)
        #return

        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//div[@class="category-products"]/ul/li/a/@href').extract(): ###
            yield Request(url, callback=self.parse_fl_product)

        #Crawl next page.
        #return ###
        tmp = hxs.select('//div[@class="pages"]/ol/li/a[@title="Next"]/@href').extract()
        if tmp:
            yield Request(tmp[0], callback=self.parse_fl_products_list)

    def parse_fl_product(self, response):
        #inspect_response(response, self)
        #return

        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        tmp = hxs.select('//input[@name="product"]/@value').extract()
        if tmp:
            loader.add_value('identifier', tmp[0])
            loader.add_value('sku', tmp[0])
        else:
            log.msg('### No product ID at '+response.url, level=log.INFO)
            return
        #tmp = hxs.select('//input[@name="/atg/store/order/purchase/CartFormHandler.productId"]/@value').extract()
        #if tmp:
        #    loader.add_value('sku', tmp[0])
        name = ''
        tmp = hxs.select('//div[@class="product-name"]/h1/text()').extract()
        if tmp:
            name = tmp[0].strip()
            loader.add_value('name', name)
        else:
            log.msg('### No name at '+response.url, level=log.INFO)
        #price
        price = 0
        stock = 0
        tmp = hxs.select('//div[@class="product-shop"]//span[@class="price"]/text()').extract()
        if tmp:
            price = extract_price(tmp[0].strip().replace(',',''))
            loader.add_value('price', price)
            stock = 1
        #stock
        #tmp = hxs.select('//form[@id="save-product-to-cart"]//p[not(contains(@class,"hidden"))]/strong[text()="Out of stock"]')
        #if tmp:
        #    stock = 0
        loader.add_value('stock', stock)
        #image_url
        tmp = hxs.select('//div[@class="product-img-box"]//img[1]/@src').extract()
        if tmp:
            url = urljoin(response.url, tmp[0])
            loader.add_value('image_url', url)
        #brand
        #tmp = hxs.select('//h1[@class="catalog_link"]/span[@itemprop="brand"]/text()').extract()
        #if tmp:
        #    loader.add_value('brand', tmp[0].strip())
        #category
        tmp = hxs.select('//div[@class="breadcrumbs"]/ul/li/a/text()').extract()
        if len(tmp)>1:
            for s in tmp[1:]:
                loader.add_value('category', s.strip())
        #shipping_cost
        tmp = hxs.select('//dd[contains(@class,"deliveryMethod")]/ul/li[contains(input/@class,"dpdsunday")]//label[text()="Timed Delivery "]//span[@class="price"]/text()').extract()
        if tmp:
            loader.add_value('shipping_cost', extract_price(tmp[0].strip().replace(',','')))

        product = loader.load_item()

        #metadata = YMeta()
        #tmp = hxs.select('//p[@class="price-off-and-save"]//text()').extract()
        #if tmp:
        #    metadata['promotions'] = ' '.join([s.strip() for s in tmp if s.strip()])
        #product['metadata'] = metadata

        options = hxs.select('//dd[@class="size "]/ul/li')
        #process options
        if options:
            for sel in options: ###
                item = copy.deepcopy(product)
                tmp = sel.select('.//input[@type="radio"]/@value').extract()
                if tmp:
                    item['identifier'] += '-' + tmp[0]
                tmp = sel.select('.//span[@class="label"]/label/text()').extract()
                if tmp:
                    item['name'] = name + ' - ' + tmp[0].strip()
                tmp = sel.select('.//span[@class="price"]/text()').extract()
                if tmp:
                    pr = extract_price(tmp[0].strip().replace(',',''))
                    item['price'] = price + pr
                    item['stock'] = 1

                if not item.get('identifier', None):
                    log.msg('### No product ID at '+response.url, level=log.INFO)
                else:
                    if not item['identifier'] in self.id_seen:
                        self.id_seen.append(item['identifier'])
                        yield item
                    else:
                        log.msg('### Duplicate product ID at '+response.url, level=log.INFO)
            return

        #no options
        if not product.get('identifier', None):
            log.msg('### No product ID at '+response.url, level=log.INFO)
        else:
            if not product['identifier'] in self.id_seen:
                self.id_seen.append(product['identifier'])
                yield product
            else:
                log.msg('### Duplicate product ID at '+response.url, level=log.INFO)

