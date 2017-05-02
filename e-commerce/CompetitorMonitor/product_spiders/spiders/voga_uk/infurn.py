import re
import csv
from StringIO import StringIO
import json
from decimal import Decimal

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector, XmlXPathSelector
from scrapy.http import Request, FormRequest
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from scrapy.http.cookies import CookieJar
from scrapy import log

import re


class InfurnUKSpider(BaseSpider):
    name = 'voga_uk-infurn.com'
    allowed_domains = ['infurn.com']
    #start_urls = ('http://www.infurn.com/en/beanbag-dog-bed-the-original', )
    start_urls = ('http://www.infurn.com/en',)
    retries = {}

    def change_currency(self):
        yield FormRequest(url='http://www.infurn.com/files/xajax/product.php',
                             formdata=(('xjxfun', 'change_currency'),
                                       ('xjxargs[]', 'GBP'), ('xjxargs[]', '<![CDATA[/xx]]>')),
            callback=self.change_currency, dont_filter=True)

    def change_currency(self, response):
        p = response.meta['prod_url']
        yield Request(p, meta={'category': response.meta.get('category', ''), 'cookiejar': p}, callback=self.parse_product)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        
        cats = hxs.select('//div[@class="listcat"]//a')
        for c in cats:
            yield Request(c.select('./@href').extract()[0], meta={'category': c.select('./text()').extract()[0].split('(')[0].strip()})

        products = hxs.select('//div[@class="details"]//a[@class="website"]/@href').extract()
        for p in products:
            yield FormRequest(url='http://www.infurn.com/files/xajax/product.php',
                                         formdata=(('xjxfun', 'change_currency'),
                                                   ('xjxargs[]', 'GBP'), ('xjxargs[]', '<![CDATA[/xx]]>')),
                              meta={'category': response.meta.get('category', ''), 'cookiejar': p, 'prod_url': p},
                              callback=self.change_currency, dont_filter=True)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        options = hxs.select('//form[@id="variations"]//select')

        base_name = hxs.select('//h1//text()').extract()[0].strip() + ' ' + hxs.select('//h1//text()').extract()[1].strip()
        brand = hxs.select('//h1//text()').extract()[0].strip()
        url = response.url
        product_id = hxs.select('//span[@id="site_info_container"]/text()').extract()[0].split(';')[-1]
        image_url_id = hxs.select('//input[@id="galery_large_media_id"]/@value').extract()[0]
        image_url = 'http://cdn4.infurn.com/images/standard/%s/--/--.jpg' % image_url_id

        if not options:
            p = ProductLoader(item=Product(), response=response)
            p.add_value('identifier', product_id)
            p.add_value('name', base_name)
            p.add_value('brand', brand)
            p.add_value('url', url)
            p.add_value('image_url', image_url)
            p.add_value('price', hxs.select('//div[@id="discounted_price"]/text()').extract()[0])
            p.add_value('shipping_cost', '0')
            p.add_value('category', response.meta.get('category'))
            yield p.load_item()
            return

        requests = self.get_request_sequences(options[0], options[1:], [[]], product_id, 0)
        colors = self.get_default_colors(hxs, options)

        r = self.construct_option_request(requests[0][0], {'current': requests[0][1:], 'next': requests[1:], 'current_data': [requests[0][0]],
                                                           'base_name': base_name, 'brand': brand, 'url': url, 'image_url': image_url,
                                                           'product_id': product_id, 'category': response.meta.get('category', ''), 'cookiejar': response.meta.get('cookiejar'),
                                                           'default_colors': colors})

        yield r

    def get_default_colors(self, hxs, options):
        colors = {}
        for n, o in enumerate(options):
            opt_id = o.select('.//@id').extract()[0].replace('varselect', '')
            colors_text = '\n'.join(hxs.select('.//div[@id="v' + opt_id + '"]/img/@onclick').extract())
            r = re.findall('''do_var_selection\('.*?~(.*?)~''', colors_text, re.MULTILINE)
            r2 = re.findall('''do_var_selection\('(.*?)~''', colors_text, re.MULTILINE)
            colors[n] = {'colors_ids': r2, 'colors': r}

        return colors

    def construct_option_request(self, data, meta):
        return FormRequest(url='http://www.infurn.com/files/xajax/product.php',
                             formdata=(('xjxfun', 'get_variation_dropdown_x'),
                                       ('xjxargs[]', data['opt_id']), ('xjxargs[]', data['opt_select_id']), ('xjxargs[]', str(data['n']) if data['n'] else ''),
                                       ('xjxargs[]', data['product_id'])), meta=meta, callback=self.parse_options, dont_filter=True)

    def parse_options(self, response):
        n = len(response.meta['current_data']) - 1
        opt_name = response.meta['current_data'][-1]['opt_name']
        colors = response.meta.get('colors', {})
        colors_ids = response.meta.get('colors_ids', {})
        hxs = XmlXPathSelector(response)

        r = re.findall('''onclick="do_var_selection\('.*?~(.*?)~''', response.body, re.MULTILINE)
        r2 = re.findall('''onclick="do_var_selection\('(.*?)~''', response.body, re.MULTILINE)

        if r:
            colors[str(n) + ':' + opt_name] = r
            colors_ids[str(n) + ':' + opt_name] = r2
        else:
            res = response.meta.get('default_colors').get(n)
            if res['colors']:
                colors[str(n) + ':' + opt_name] = res['colors']
                colors_ids[str(n) + ':' + opt_name] = res['colors_ids']

        if not response.meta['current']:
            for product in self.get_products(response.meta, response, colors, colors_ids):
                yield product
            if response.meta['next']:
                requests = response.meta['next']
                r = self.construct_option_request(requests[0][0], {'current': requests[0][1:], 'next': requests[1:], 'current_data': [requests[0][0]],
                                                                   'base_name': response.meta['base_name'], 'brand': response.meta['brand'], 'url': response.meta['url'],
                                                                   'image_url': response.meta['image_url'], 'colors': colors, 'colors_ids': colors_ids, 'product_id': response.meta['product_id'],
                                                                   'category': response.meta.get('category', ''), 'cookiejar': response.meta.get('cookiejar'),
                                                                   'default_colors': response.meta.get('default_colors')})
                yield r
        else:
            current_data = response.meta['current_data'] + [response.meta['current'][0]]
            r = self.construct_option_request(response.meta['current'][0], {'current': response.meta['current'][1:], 'next': response.meta['next'], 'current_data': current_data,
                                                                            'base_name': response.meta['base_name'], 'brand': response.meta['brand'], 'url': response.meta['url'],
                                                                            'image_url': response.meta['image_url'], 'colors': colors, 'colors_ids': colors_ids,
                                                                            'product_id': response.meta['product_id'], 'category': response.meta.get('category', ''),
                                                                            'cookiejar': response.meta.get('cookiejar'),
                                                                            'default_colors': response.meta.get('default_colors')})
            yield r

    def get_products(self, meta, response, colors, colors_ids):
        hxs = XmlXPathSelector(response)
        names, ids = self.get_names(meta['base_name'], meta['product_id'], meta['current_data'], colors, colors_ids)

        for i, name in enumerate(names):
            p = ProductLoader(item=Product(), response=response)
            p.add_value('identifier', ids[i])
            p.add_value('name', name)
            p.add_value('brand', meta['brand'])
            p.add_value('url', meta['url'])
            p.add_value('image_url', meta['image_url'])
            price = hxs.select('//cmd[@t="discounted_price"]/text()').extract()
            if price:
                price = price[0]
                price = extract_price(price)
            if not price or price == Decimal(1):
                if not price:
                    self.log('Price not found %s' % meta['url'])
                else:
                    self.log('Price is one %s' % meta['url'])

                if not self.retries.get(meta['url']) or self.retries.get(meta['url']) < 3:
                    self.log('Retrying %s' % meta['url'])
                    self.retries[meta['url']] = self.retries.get(meta['url'], 0) + 1
                    p = meta['url']
                    yield Request(p, meta={'category': response.meta.get('category', ''),
                                           'cookiejar': p + str(self.retries.get(meta['url']))},
                                            callback=self.parse_product, dont_filter=True)
                else:
                    self.log('Max retries reached %s' % meta['url'])
                return
            p.add_value('price', price)
            p.add_value('shipping_cost', '0')
            p.add_value('category', response.meta.get('category'))
            yield p.load_item()

    def get_names(self, base_name, base_identifier, current_data, colors, colors_ids, n=0):
        if not current_data:
            return [base_name], [base_identifier]

        r = current_data[0]
        k = str(n) + ':' + r['opt_name']

        ids = []
        names = []
        if k in colors:
            for i, color in enumerate(colors[k]):
                current_name = u'%s / %s %s' % (base_name, r['opt_name'], color.decode('utf8'))
                res = self.get_names(current_name, base_identifier + '-' + r['opt_id'] + '-' + colors_ids[k][i],
                                     current_data[1:], colors, colors_ids, n + 1)
                names += res[0]
                ids += res[1]

        else:
            res = self.get_names(base_name + ' / ' + r['opt_name'], base_identifier + '-' + r['opt_id'], current_data[1:], colors,  colors_ids, n + 1)
            names += res[0]
            ids += res[1]

        return names, ids


    def get_request_sequences(self, current_options, additional_options, current_sequence, product_id, n):
        req = []
        opt_select_id = current_options.select('.//@id').extract()[0].replace('varselect', '')
        for c in current_options.select('.//option'):
            opt_name = c.select('./text()').extract()[0]
            opt_id = c.select('.//@value').extract()[0]

            req.append({'opt_name': opt_name.strip(), 'opt_id': opt_id, 'opt_select_id': opt_select_id, 'n': n, 'product_id': product_id})

        new_seq = []
        for c1 in current_sequence:
            for c2 in req:
                new_seq.append(c1 + [c2])

        if additional_options:
            return self.get_request_sequences(additional_options[0], additional_options[1:], new_seq[:], product_id, n + 1)
        else:
            return new_seq[:]
