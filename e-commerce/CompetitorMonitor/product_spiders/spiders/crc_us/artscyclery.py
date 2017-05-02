# -*- coding: utf-8 -*-
import re
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import FormRequest, Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals
from scrapy.exceptions import DontCloseSpider
from w3lib.url import url_query_cleaner

from product_spiders.spiders.pedalpedal.crcitem import CRCMeta


class ArtscyclerySpider(BaseSpider):
    name = u'artscyclery.com'
    allowed_domains = ['www.artscyclery.com']
    start_urls = [
        'http://www.artscyclery.com/brands.html?ctype=MRD',
        'http://www.artscyclery.com/brands.html?ctype=MMT'
    ]
    jar_counter = 0

    def __init__(self, *args, **kwargs):
        super(ArtscyclerySpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.process_all_products, signals.spider_idle)
        self.get_brandless_products = 1

    def process_all_products(self, spider):
        if spider.name == self.name and self.get_brandless_products:
            self.get_brandless_products = 0
            self.log("Spider idle. Processing all products")
            for url in self.start_urls:
                r = Request(url, callback=self.parse_categories)
                self._crawler.engine.crawl(r, self)
            raise DontCloseSpider

    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        urls = response.xpath('//div[@class="catmenu"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_subcategories)

    def parse_subcategories(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in hxs.select('//div[@class="catmenu"]//ul[@class="submenu"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_subcategories)
        for url in hxs.select('//div[@class="product_name"]//a/@href').extract():
            self.jar_counter += 1
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_product,
                          cookies={},
                          meta={'cookiejar': self.jar_counter, 'brand': ''})

        urls = hxs.select('//div[@class="brandtable"]//a/@href').extract()
        brands = hxs.select('//div[@class="brandtable"]//a/text()').extract()
        for url, brand in zip(urls, brands):
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list, meta={'brand': brand})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        urls = response.xpath('//div[@class="brandtable"]//a/@href').extract()
        brands = hxs.select('//div[@class="brandtable"]//a/text()').extract()
        for url, brand in zip(urls, brands):
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list, meta={'brand': brand})

    def parse_products_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        brand = response.meta.get('brand')
        for url in hxs.select('//div[@class="product_name"]//a/@href | //div[@class="product_features"]/h3/a/@href').extract():
            self.jar_counter += 1
            yield Request(url_query_cleaner(response.urljoin(url)),
                          callback=self.parse_product,
                          cookies={},
                          meta={'cookiejar': self.jar_counter, 'brand': brand})
        for url in hxs.select('//ul[@class="catthumb_list clearfix"]//div[@class="title"]/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list)


    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        image_url = hxs.select('//img[@class="mainimage"]/@src').extract()
        brand = response.meta.get('brand')
        product_name = hxs.select('//h1[@class="name"]/text()').extract()[0].strip()
        price = hxs.select('//*[@id="product_price"]/span[@class="price"]/text()').extract()
        rrp = hxs.select('//span[@class="msrptext"]/text()').extract()
        rrp = str(extract_price(rrp[0])) if rrp else ''
        if not price:
            product_loader = ProductLoader(item=Product(), selector=hxs)
            identifier = hxs.select('//*[@id="ordering_area"]/input[@name="pcode"]/@value').extract()
            if not identifier:
                self.log("No identifier!!! url: {}".format(response.url))
                return
            product_loader.add_value('identifier', identifier[0])
            product_loader.add_value('sku', identifier[0])
            product_loader.add_value('name', product_name)
            stock = hxs.select('//*[@id="order_alert"]/span/text()').extract()[0]
            stock = stock.replace('+', '')
            try:
                stock = int(stock)
            except:
                pass
            else:
                product_loader.add_value('stock', stock)
            product_loader.add_value('url', response.url)
            product_loader.add_value('brand', brand)
            if image_url:
                product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            product = product_loader.load_item()
            metadata = CRCMeta()
            metadata['rrp'] = rrp
            product['metadata'] = metadata
            yield FormRequest.from_response(response,
                                            formnumber=1,
                                            dont_filter=True,
                                            dont_click=True,
                                            callback=self.parse_basket,
                                            meta={'product': product,
                                                  'cookiejar': response.meta['cookiejar']})
            return
        price = extract_price(price[0])

        identifiers = re.findall('google_tag_params.ecomm_prodid.push\(\'([^\']*)\'\);', response.body)
        identifiers += re.findall('google_tag_params.ecomm_prodid = \'([^\']*)\';', response.body)

        options = hxs.select('//*[@id="ordering_replace"]//select[@name="pcode"]//option')
        man_num = re.search("part # ([a-zA-Z0-9\-]+)</li>", response.body.replace("&nbsp;", " "))
        if options:
            for option in options:
                product_loader = ProductLoader(item=Product(), selector=option)
                identifier = option.select('./@value').extract()[0]
                if not identifier:
                    continue
                product_loader.add_value('sku', identifier)
                product_loader.add_value('identifier', identifier)
                option_name = option.select('./text()').extract()[0].strip()
                parts = option_name.partition(' - In stock: ')
                name = parts[0]
                product_loader.add_value('name', name)
                #stock = parts[2]
                if image_url:
                    product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
                product_loader.add_value('price', price)
                product_loader.add_value('url', response.url)
                product_loader.add_value('brand', brand)
                product = product_loader.load_item()
                metadata = CRCMeta()
                if man_num:
                    metadata['manufacturer_number'] = man_num.group(1).strip()
                metadata['rrp'] = rrp
                product['metadata'] = metadata
                yield product
        else:
            rows = hxs.select('//table[@class="ordering_table"]//tr')
            if len(rows) > 1:
                for i, row in enumerate(rows[1:]):
                    product_loader = ProductLoader(item=Product(), selector=hxs)
                    name1 = row.select('./td[1]/text()').extract()[0].strip()
                    name2 = row.select('./td[7]/text()').extract()[0].strip()
                    name = "{}, {}, {}".format(product_name, name1, name2)
                    product_loader.add_value('name', name)
                    identifier = row.select('./td[10]/input/@name').extract()
                    if identifier:
                        identifier = identifier[0]
                    else:
                        identifier = identifiers[i]
                    product_loader.add_value('sku', identifier)
                    product_loader.add_value('identifier', identifier)
                    stock = row.select('./td[8]/span/text()').extract()[0].strip()
                    stock = stock.replace('+', '')
                    try:
                        stock = int(stock)
                    except:
                        pass
                    else:
                        product_loader.add_value('stock', stock)
                    price = row.select('./td[9]/text()').extract()[0].strip()
                    product_loader.add_value('price', extract_price(price))
                    product_loader.add_value('url', response.url)
                    product_loader.add_value('brand', brand)
                    if image_url:
                        product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
                    product = product_loader.load_item()
                    metadata = CRCMeta()
                    if man_num:
                        metadata['manufacturer_number'] = man_num.group(1).strip()
                    metadata['rrp'] = rrp
                    product['metadata'] = metadata
                    yield product
                return
            else:
                rows = hxs.select('//table[@class="ordering_table road_tire_table"]//tr')
                if len(rows) > 1:
                    titles = {}
                    header = rows[0].select('./th')
                    i = 0
                    for title in header.select('string(.)').extract():
                        i += 1
                        titles[title] = i
                    for i, row in enumerate(rows[1:]):
                        product_loader = ProductLoader(item=Product(), selector=hxs)
                        name1 = row.select('./td[{}]/text()'.format(titles['Color'])).extract()
                        if name1:
                            name = "{}, {}".format(product_name, name1[0].strip())
                        else:
                            name = product_name
                        product_loader.add_value('name', name)
                        identifier = row.select('./td[{}]/input/@name'.format(titles['Qty'])).extract()
                        if identifier:
                            identifier = identifier[0]
                        else:
                            identifier = identifiers[i]
                        product_loader.add_value('sku', identifier)
                        product_loader.add_value('identifier', identifier)
                        stock = row.select('./td[{}]/span/text()'.format(titles['Stock'])).extract()
                        if stock:
                            stock = stock[0].strip().replace('+', '')
                            try:
                                stock = int(stock)
                            except:
                                pass
                            else:
                                product_loader.add_value('stock', stock)
                        else:
                            stock = row.select('./td[{}]/text()'.format(titles['Stock'])).extract()[0].strip()
                            if stock == 'Out of Stock':
                                product_loader.add_value('stock', 0)
                            else:
                                self.log('Unknown text: {}'.format(stock))
                        price = row.select('./td[{}]/text()'.format(titles['Price'])).extract()[0].strip()
                        product_loader.add_value('price', extract_price(price))
                        product_loader.add_value('url', response.url)
                        product_loader.add_value('brand', brand)
                        if image_url:
                            product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
                        product = product_loader.load_item()
                        metadata = CRCMeta()
                        if man_num:
                            metadata['manufacturer_number'] = man_num.group(1).strip()
                        metadata['rrp'] = rrp
                        product['metadata'] = metadata
                        yield product
                    return
                
                rows = response.xpath('//table[@class="styled_subproduct_list"]//tr')
                if rows:
                    for i, row in enumerate(rows):
                        product_loader = ProductLoader(item=Product(), selector=hxs)
                        name = row.xpath('.//span/strong/text()').extract_first()
                        product_loader.add_value('name', name)
                        identifier = row.select('.//input/@value').extract_first()
                        if not identifier:
                            identifier = identifiers[i]
                        product_loader.add_value('sku', identifier)
                        product_loader.add_value('identifier', identifier)
                        stock = row.css('.available ::text').extract_first()
                        if 'Out' in stock:
                            product_loader.add_value('stock', 0)
                        #price = row.select('./td[9]/text()').extract()[0].strip()
                        product_loader.add_value('price', price)
                        product_loader.add_value('url', response.url)
                        product_loader.add_value('brand', brand)
                        if image_url:
                            product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
                        product = product_loader.load_item()
                        metadata = CRCMeta()
                        if man_num:
                            metadata['manufacturer_number'] = man_num.group(1).strip()
                        metadata['rrp'] = rrp
                        product['metadata'] = metadata
                        yield product
                    return

            product_loader = ProductLoader(item=Product(), selector=hxs)
            identifier = hxs.select('//*[@id="ordering_area"]/input[@name="pcode"]/@value | //*[@id="feedback_bar"]//input[@name="pcode"]/@value').extract()
            if not identifier:
                self.log("No identifier!!! url: {}".format(response.url))
                return
            product_loader.add_value('identifier', identifier[0])
            product_loader.add_value('sku', identifier[0])
            product_loader.add_value('name', product_name)
            stock = hxs.select('//*[@id="order_alert"]/span/text()').extract()
            if stock:
                stock = stock[0].replace('+', '')
                try:
                    stock = int(stock)
                except:
                    pass
                else:
                    product_loader.add_value('stock', stock)
            product_loader.add_value('price', price)
            product_loader.add_value('url', response.url)
            product_loader.add_value('brand', brand)
            if image_url:
                product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            product = product_loader.load_item()
            metadata = CRCMeta()
            if man_num:
                metadata['manufacturer_number'] = man_num.group(1).strip()
            metadata['rrp'] = rrp
            product['metadata'] = metadata
            yield product

    def parse_basket(self, response):
        hxs = HtmlXPathSelector(response)
        product = response.meta['product']
        price = hxs.select('//*[@id="ordercart"]//td[@class="iprice"]/text()').extract()[0].strip()
        product['price'] = extract_price(price)
        yield product
