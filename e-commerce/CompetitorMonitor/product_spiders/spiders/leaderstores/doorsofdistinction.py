"""
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4475

The site is made on tables, no tags id's, a few tags names. Mostly parsed based on tables elements colour and text containing. There are a lot of different pages with different tables structure.
"""

from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
import re

class DoorsofDistinction(BaseSpider):
    name = "doorsofdistinction.co.uk"
    allowed_domains = ['doorsofdistinction.co.uk']
    start_urls = ['http://www.doorsofdistinction.co.uk/index.siteIndex.html']
    
    ids_seen = []
    treatment = False
   
    def parse(self, response):
        for url in response.xpath('//table//a/@href').extract():
            yield Request(urljoin(get_base_url(response), url.lstrip('..')), callback=self.parse_categories)
            
    def parse_categories(self, response):
        base_url = get_base_url(response)
        categories = response.xpath('//a[img/@alt="back to previous page"]/@href').extract()
        categories += response.xpath('//a[img/@alt="next door page"]/@href').extract()
        for url in categories:
            yield Request(urljoin(base_url, url), callback=self.parse_categories)
        
        products = response.xpath('//a[img]/@href').extract()
        for url in products:
            if url.endswith('html'):
                yield Request(urljoin(base_url, url.lstrip('..')), callback=self.parse_products)
            
    def parse_products(self, response):
        try:
            base_url = get_base_url(response)
        except AttributeError:
            return
        
        if response.xpath('//font[contains(text(), "Recommended Door Treatment")]') and not self.treatment:
            for treatment in self.parse_treatment(response):
                yield treatment
                
        identifiers = []
        price_found = False
        for product in response.xpath('//td[@bgcolor="#E5E5E5"]//table/tr[contains(., "Code:")]') or response.xpath('//td[@bgcolor="#FFFFFF"]//table/tr[contains(., "Code:")]'):
            loader = ProductLoader(item=Product(), selector=product)
            loader.add_value('url', response.url)
            product_name = ' '.join(product.xpath('.//text()').re('\S+'))
            sku = re.findall('Code: *([^:]+)$', product_name)
            if not sku:
                self.log('No SKU found for %s on %s' %(product_name, response.url))
                continue
            sku = sku[0].replace(' ', '')
            loader.add_value('sku', sku)
            item = loader.load_item()
            price = ''
            for size in product.xpath('./following-sibling::tr'):
                if size.xpath('.//*[contains(.//text(), "Code:")]'):
                    break
                if not size.xpath('./td[contains(.//text(), " x")]'):
                    try:
                        price = size.xpath('td[3]//td/text()').extract()[-1]
                    except IndexError:
                        pass
                    continue
                size_name = size.xpath('td[1]//text()').extract()
                if not size_name:
                    continue
                loader = ProductLoader(item=Product(item), selector=size)
                loader.add_value('name', product_name)
                loader.add_value('name', size_name)
                if size.xpath('td[3]'):
                    try:
                        price = size.xpath('td[3]//td/text()').extract()[-1]
                    except IndexError:
                        pass
                if not price:
                    #self.log('No price found for %s %s on %s' %(product_name, size_name, response.url))
                    continue
                price_found = True
                loader.add_value('price', price)
                identifier = sku + '-' + '-'.join(re.findall('\d+', size_name[0]))
                identifier += '-' + response.url.split('/')[-1].split('_')[0].split('.')[0]
                #avoiding duplicated identifiers
                if identifier in identifiers or identifier in self.ids_seen:
                    identifier += '-d'
                identifiers.append(identifier)
                self.ids_seen.append(identifier)
                loader.add_value('identifier', identifier)
                final_item = loader.load_item()
                image_url = response.xpath('//*[contains(text(), "Click on")]/../../..//img/@src').extract() or response.xpath('//td[@bgcolor="#E5E5E5"]//img/@src').extract()
                for image in response.xpath('//*[@class="doorname"]'):
                    image_name = image.xpath('font/text()').extract()
                    if image_name and image_name[0].strip() in final_item['name']:
                        image_url = image.xpath('./../p[2]//img/@src').extract() or image.xpath('./../../p[2]//img/@src').extract()
                        if image_url:
                            break
                final_item['image_url'] = urljoin(base_url, image_url[0])
                yield loader.load_item()
        if price_found:
            return
        
        for url in response.xpath('//a[img]/@href').extract():
            if url.endswith('html'):
                yield Request(urljoin(base_url, url), callback=self.parse_products)
        try:
            product = response.xpath('//td[@class="Pricegridlabel"]')[0]
        except IndexError:
            for product in self.parse_frames(response):
                yield product
            return
        identifiers = []
        name = ' '.join(product.xpath('./following-sibling::td[1]//text()').extract())
        image_url = response.xpath('//*[contains(text(), "Click on")]/../preceding-sibling::*[1]//img/@src').extract() or response.xpath('//img[contains(@alt, "door")]/@src').extract()
        found_sku = False
        for i, option in enumerate(product.xpath('./../following-sibling::tr[1]/td')):
            option_name = ' '.join(option.xpath('.//text()').extract())
            code = ''.join(option.xpath('./../following-sibling::tr[1]/td[%d]//text()' %(i+1)).extract())
            sku = ''.join(re.findall('CODE: *([^: ]+)$', code))
            if not sku:
                continue
            found_sku = True
            for size in option.xpath('./../following-sibling::tr'):
                if not size.xpath('./td[1][contains(.//text(), " x")]'):
                    continue
                size_name = size.xpath('td[1]//text()').extract()
                loader = ProductLoader(item=Product(), selector=size)
                loader.add_value('name', (name, option_name))
                loader.add_value('name', size_name)
                loader.add_value('sku', sku)
                identifier = sku + '-' + '-'.join(re.findall('\d+', size_name[0]))
                identifier += '-' + response.url.split('/')[-1].split('_')[0].split('.')[0]
                #avoiding duplicated identifiers
                while identifier in identifiers or identifier in self.ids_seen:
                    identifier += '-d'
                identifiers.append(identifier)
                self.ids_seen.append(identifier)
                loader.add_value('identifier', identifier)
                loader.add_xpath('price', 'td[%d]//text()' %(i+2))
                if image_url:
                    loader.add_value('image_url', urljoin(base_url, image_url[0]))
                loader.add_value('url', response.url)
                yield loader.load_item()
        if not found_sku:
            for product in self.parse_frames(response):
                yield product
                
    def parse_frames(self, response):
        base_url = get_base_url(response)
        products = response.xpath('//tr/td[text()="Code"][1]')
        if products:
            margin = 3
        else:
            products = response.xpath('//tr/td[span/text()="CODE"][1]')
            if products:
                margin = 2
        if not products:
            self.log('No products found on %s' %response.url)
        identifiers = []
        image_url = response.xpath('//img[not (contains(@alt, "Doors"))]/@src[contains(., "images-thumb")]').extract()
        for product in products:
            for idx, option in enumerate(product.xpath('./../preceding-sibling::tr[1]/td[position()>1]')):
                name = option.xpath('.//text()').extract()
                for size in product.xpath('./../following-sibling::tr'):
                    if size.xpath('td[(text()="Code") or (span/text()="CODE")]'):
                        break
                    if not size.xpath('./td[1][contains(.//text(), " x")]'):
                        continue
                    loader = ProductLoader(item=Product(), selector=size)
                    loader.add_value('name', name)
                    size_name = size.xpath('td[1]/text()').extract()
                    loader.add_value('name', size_name)
                    loader.add_xpath('sku', 'td[%d]/text()' %(idx*2+margin))
                    loader.add_xpath('price', 'td[%d]/text()' %(idx*2+margin+1))
                    if not loader.get_output_value('sku'):
                        continue
                    identifier = loader.get_output_value('sku') + '-' + '-'.join(re.findall('\d+', size_name[0]))
                    identifier += '-' + response.url.split('/')[-1].split('_')[0].split('.')[0]
                    while identifier in identifiers or identifier in self.ids_seen:
                        identifier += '-d'
                    identifiers.append(identifier)
                    self.ids_seen.append(identifier)
                    loader.add_value('identifier', identifier)
                    loader.add_value('url', response.url)
                    if image_url:
                        loader.add_value('image_url', urljoin(base_url, image_url[0]))
                    yield loader.load_item()
                    
    def parse_treatment(self, response):
        base_url = get_base_url(response)
        product = response.xpath('//tr/td[(text()="Code")][1]')[0]
        identifiers = []
        for size in product.xpath('./../following-sibling::tr[position()<5]'):
            loader = ProductLoader(item=Product(), selector=size)
            size_name = size.xpath('td[1]/text()').extract()
            loader.add_value('name', size_name)
            loader.add_xpath('sku', 'td[2]/text()')
            loader.add_xpath('price', 'td[3]/text()')
            if not loader.get_output_value('sku'):
                continue
            loader.add_xpath('identifier', 'td[2]/text()')
            loader.add_value('url', response.url)
            yield loader.load_item()
        else:
            self.treatment = True