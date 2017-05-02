# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.url import add_or_replace_parameter
import re
import json
import itertools
import copy
import datetime

from scrapy import log

from bikenationmeta import BikeNationMeta


def mk_int(s):
    s = s.strip()
    try:
        result = int(s) if s else 0
    except:
        result = 0
    return result


class GetgearedSpider(BaseSpider):
    name = u'getgeared.co.uk'
    allowed_domains = ['www.getgeared.co.uk', 'forms.netsuite.com']
    wizard_url = "https://forms.netsuite.com/app/site/hosting/scriptlet.nl?script=6&deploy=1&compid=731612&h=e4f6852febb221829378"
    errors = []

    def start_requests(self):
        yield Request('http://www.getgeared.co.uk/', callback=self.parse)
        yield Request('http://www.getgeared.co.uk/sitemap.html', callback=self.parse_sitemap)

    def parse_sitemap(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in hxs.select('//a[@itemprop="url"]/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_categories)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in hxs.select('//nav//a[@class="celllink"]/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_categories)

    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        wizard = hxs.select('//script[contains(@src, "bb1_brandmodel_script.js")]/@src').extract()
        if wizard:
            match = re.search(r'var bb1_catid = "(\d+)";', response.body)
            if match:
                result = match.group(1)
                url = add_or_replace_parameter(self.wizard_url, 'id', result)
                yield Request(url, callback=self.parse_wizard)
            else:
                self.log('ERROR! No match for bb1_catid, url: {}'.format(response.url))
                return
        else:
            for url in hxs.select('//a[@class="subcatlink"]/@href').extract():
                yield Request(urljoin_rfc(base_url, url), callback=self.parse_categories)
            for url in hxs.select('//div[@class="itemlistcell_overlay_on"]//a/@href').extract():
                yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)
            for url in hxs.select('//td/a[contains(@href, "?range=")]/@href').extract():
                yield Request(urljoin_rfc(base_url, url), callback=self.parse_categories)

    def parse_wizard(self, response):
        match = re.search(r'var json_brandmodel_suitelet = ({.*});', response.body)
        if match:
            result = match.group(1)
            data = json.loads(result)
            if data['stage'] != '4':
                for result in data['results']:
                    urlparams = result['urlparms']
                    urlparams = dict(itertools.izip_longest(*[iter(urlparams)] * 2, fillvalue=""))
                    url = response.url
                    for param, value in urlparams.iteritems():
                        if data['stage'] == '3' and param == 'model':
                            param = 'modelid'
                        url = add_or_replace_parameter(url, param, value)
                    yield Request(url, callback=self.parse_wizard)
            else:
                for result in data['results']:
                    yield Request(result['itemurl'], callback=self.parse_product)

        else:
            self.log('ERROR! No match for json_brandmodel_suitelet, url: {}'.format(response.url))
            return

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        price = hxs.select('//span[@class="price"]/text()').extract()
        name = hxs.select('//h1[@itemprop="name"]/text()').extract()
        if not name and not price:
            # self.errors.append("Name and price not found, posibly wrong page on %s" % response.url)
            return
        price = extract_price(price.pop())
        name = name.pop()
        match = re.search(r'productpicbig\.src=["\'](.*)["\'];', response.body)
        if match:
            image_url = match.group(1)
        else:
            image_url = None
        category = hxs.select('//a[@class="crumb"][1]/text()').extract()
        category = category[0].strip() if category else ''
        brand = hxs.select('//span[@itemprop="brand"]/@content').extract()
        brand = brand[0].strip() if brand else ''

        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('name', name)
        if image_url:
            product_loader.add_value('image_url', urljoin_rfc(base_url, image_url))
        product_loader.add_value('price', price)
        product_loader.add_value('url', response.url)
        product_loader.add_value('brand', brand)
        product_loader.add_value('category', category)
        sku = hxs.select('//span[@itemprop="identifier" or @itemprop="productID"]/text()').extract()[0]
        product_loader.add_value('sku', sku)
        prices = {}
        options = hxs.select('//*[@id="item-options"]').extract()
        if options:
            for match in re.finditer(r"Item(?:\d+)?_prices\['(\d+)'\]='(.*?)';", options[0]):
                prices[match.group(1)] = match.group(2)
        product = product_loader.load_item()
        url = hxs.select('//script[contains(@src, "script=1&")]/@src').extract()
        if url:
            yield Request(urljoin_rfc(base_url, url.pop()), meta={'product': product, 'prices': prices}, callback=self.parse_stock)

    def parse_stock(self, response):
        product_data = response.meta['product']
        prices = response.meta['prices']
        match = re.search(r'var bb1_qtyavailable_matrix = ({.*});', response.body)

        weekno = datetime.date.today().isocalendar()[1]

        if match:
            json_data = json.loads(match.group(1))
            match = re.search(r'var bb1_matrix_itemoptions = { "(.*?)":', response.body)
            if match:
                prop_name = match.group(1)
            else:
                self.log('WARNING!!! No prop_name name found! {}'.format(response.body))
                return
            for val, data in json_data.iteritems():

                qtyavailable = mk_int(data['qtyavailable'])
                qtyintransit = mk_int(data['qtyintransit'])
                weekavailable = mk_int(data['weekavailable'])
                product = copy.deepcopy(product_data)

                stockmessage = ''
                if (mk_int(data['qtyavailable']) + mk_int(data['qtyintransit']) >= 1):
                    stockmessage = 'In Stock'
                else:
                    if (data['specialorder'] == 'T' and (qtyavailable + qtyintransit) <= 0 and weekavailable > weekno):
                        stockmessage = 'In Stock 1-2 Day Delivery'
                    else:
                        if (data['specialorder'] == 'T' and qtyavailable + qtyintransit <= 0):
                            stockmessage = 'In Stock 1-2 Day Delivery'
                        else:
                            if (qtyavailable + qtyintransit <= 0 and weekavailable > weekno):
                                stockmessage = 'Estimated Despatch in ' + str(weekavailable - weekno) + ' weeks'
                            else:
                                if (qtyavailable + qtyintransit <= 0 and weekavailable <= weekno):
                                    stockmessage = 'Estimated Despatch in 1-2 weeks';

                product['identifier'] = data['internalid']
                product['name'] = product['name'] + ', ' + data[prop_name]['name']
                if data[prop_name]['id'] in prices:
                    product['price'] = extract_price(prices[data[prop_name]['id']])

                if product['price'] <= 0:
                    product['stock'] = 0

                metadata = BikeNationMeta()
                metadata['stock_status'] = stockmessage
                product['metadata'] = metadata

                yield product
        else:
            if 'DisplayItemStockMessage' not in response.body:
                self.log('ERROR DisplayItemStockMessage: {}'.format(response.body))
                return
            else:
                s = response.body.replace('DisplayItemStockMessage(', '').replace(');', '').replace('"', '').split(',')
                product = copy.copy(product_data)
                if product['price'] <= 0:
                    product['stock'] = 0

                product['identifier'] = response.url.partition('&itemid=')[2]

                stockmessage = ''
                if mk_int(s[1]) + mk_int(s[2]) <= 0 and s[0] != 'T':
                    stockmessage = 'Estimated Despatch in 1-2 weeks'
                else:
                    stockmessage = 'In Stock'

                metadata = BikeNationMeta()
                metadata['stock_status'] = stockmessage
                product['metadata'] = metadata
                yield product
