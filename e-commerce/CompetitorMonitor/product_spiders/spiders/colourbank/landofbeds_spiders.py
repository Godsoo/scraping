# -*- coding: utf-8 -*-

import re
from decimal import Decimal
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

def multiply(lst):
    if not lst:
        return []

    while len(lst) > 1:
        result = []
        for price0, name0, id0 in lst[0]:
            for price1, name1, id1 in lst[1]:
                result.append((float(price0) + float(price1),
                               name0 + ' ' + name1,
                               id0.replace(',', ':') + ':' + id1.replace(',', ':')))
        lst = [result] + lst[2:]
    return lst[0]

class LandOfBedsSpider(BaseSpider):
    name = "colourbank-landofbeds.co.uk"
    allowed_domains = ('landofbeds.co.uk', )
    start_urls = ('https://www.landofbeds.co.uk/includes/mega-menu.ajax.asp', )


    SKIP_OPTIONS = [
#        'http://www.landofbeds.co.uk/land-of-beds/rise-and-recline-chairs/balmoral/custom-made',
    ]

    def _start_requests(self):
        yield Request('https://www.landofbeds.co.uk/gainsborough-beds/guest-beds/pocket', callback=self.parse_product)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = response.xpath('//ul[@id="DropMenu"]//li[@id!="chairs"]//a/@href').extract()
        for cat_url in categories:
            url = urljoin_rfc(base_url, cat_url)
            if 'chairs' not in url:
                yield Request(url, callback=self.parse_list)

    def parse_list(self, response):
        hxs = HtmlXPathSelector(response)

        found = False
        for url in response.xpath('//ul[@id="ProductCatalogue"]//h2/a/@href').extract():
            found = True
            yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_product)
        if found:
            products_per_page, all_products_count = response.css('.scale::text').re('Showing \d+ to (\d+) of (\d+) Products')
            if products_per_page == all_products_count:
                return
            page = int(all_products_count)/int(products_per_page) + 1
            yield Request(response.url.split('/pg')[0] + '/pg%d' %page, callback=self.parse_list)



    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), response=response)
        sku = response.xpath('//script/text()').re('var lne_id = (.+);')
        size_id = response.xpath('//script/text()').re('var sze_id = (.+);')
        loader.add_value('sku', sku)
        loader.add_value('identifier', ':'.join(sku + size_id))
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1/text()')
        loader.add_xpath('price', '//option[@class="select-size"][@selected]/text()', re=u'\xa3(.+)')
        loader.add_value('price', 0)
        loader.add_xpath('category', '//nav[@id="Breadcrumb"]//li[3]//span/text()')
        if 'chairs' in loader.get_output_value('category').lower():
            return

        img = response.css('.imagery div.slide::attr(style)').re("background-image:url\('(.+)'\)")
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        loader.add_css('brand', 'img#BrandLogo::attr(alt)')

        if loader.get_output_value('price'):
            loader.add_value('stock', '1')
        else:
            loader.add_value('stock', '0')
        item = loader.load_item()
            
        url = 'https://www.landofbeds.co.uk/lib/json/group.json.asp?lne_id=%s&sze_id=%s' %(sku[0], size_id[0])
        if size_id[0] != '0':
            yield Request(url, self.parse_options, dont_filter=True, meta={'item': Product(item)})
        
        sizes = response.xpath('//option[@class="select-size"][not (@selected)]/@value').extract()
        for size in sizes:
            if not size or not int(size):
                continue
            yield Request('https://www.landofbeds.co.uk/lib/json/group.json.asp?lne_id=%s&sze_id=%s' %(sku[0], size), self.get_product_url)
    
    def get_product_url(self, response):
        url = response.xpath('//script/text()').re("state.fullurl = '(.+)';")
        if url:
            yield Request(response.urljoin(url[0]), self.parse_product)
        
    def parse_options(self, response):
        price_adj = {}
        for cfg in re.findall('adjustment\((\d+),(\d+),([\d.,]+)\)', response.body):
            price_adj[(cfg[0], cfg[1])] = float(cfg[2])

        # Include only options that change the price
        opt_groups = []
        for sel in response.xpath('//select[@onchange!="jump(this.value)" and @id!="quantity"]'):
            try: idx = sel.select('./@id').re('\d+')[0]
            except: continue
            opts = []
            for opt in sel.select('.//option'):

                value = opt.select('./@value').extract()[0]
                text = opt.select('normalize-space(./text())').extract()[0]
                if (idx, value) in price_adj and float(price_adj[idx, value]) != 0.0:
                    opts.append((price_adj[idx, value], text, value))
            if opts:
                opt_groups.append(opts)

        prod = response.meta['item']
        if prod.get('identifier'):
            if response.url in self.SKIP_OPTIONS or not prod['price']:
                yield self.add_shipping_cost(prod)
            else:
                yield self.add_shipping_cost(prod)
                for opt_price, opt_name, opt_id in multiply(opt_groups):
                    p = Product(prod)
                    p['name'] = p['name'] + ' ' + opt_name
                    p['price'] = p['price'] + Decimal(opt_price).quantize(Decimal('1.00'))
                    p['identifier'] = p['identifier'] + ':' + opt_id if opt_id else p['identifier'] + '-'
                    yield self.add_shipping_cost(p)      

    def add_shipping_cost(self, item):
        shipping_costs = {'Headboards': 9.99,
                         'Bed Frames': 9.99,
                         'Bunk Beds': 9.99,
                         'Bedding & Pillows': 9.99,
                         'Pillows': 9.99,
                         'Mattress Toppers': 9.99,
                         'Mattress Protectors': 9.99,
                         'Pillow Protectors': 9.99,
                         'Duvets': 9.99,
                         'Divan Beds': 19.99,
                         'Adjustable Beds': 19.99,
                         'Mattresses': 19.99,
                         'Sofa Beds': 19.99,
                         'Guest Beds': 19.99,
                         'TV Beds': 19.99}

        for category, shipping_cost in shipping_costs.iteritems():
            if category.upper() in item['category'].upper() and (not item['price'] or Decimal(item['price'])) < 100:
                item['shipping_cost'] = shipping_cost
                break

        return item
