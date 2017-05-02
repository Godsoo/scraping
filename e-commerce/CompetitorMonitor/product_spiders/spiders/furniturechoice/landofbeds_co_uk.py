import re
from decimal import Decimal
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.base_spiders.primary_spider import PrimarySpider

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

class LandOfBedsSpider(PrimarySpider):
    name = 'landofbeds.co.uk'
    allowed_domains = ['landofbeds.co.uk']
    start_urls = ['http://landofbeds.co.uk/']

    csv_file = 'landofbeds.co.uk_products.csv'

    SKIP_OPTIONS = [
#        'http://www.landofbeds.co.uk/land-of-beds/rise-and-recline-chairs/balmoral/custom-made',
    ]

    def _start_requests(self):
        yield Request('http://www.landofbeds.co.uk/kayflex/mattresses/thermo-pocket-1250/super-king-size', callback=self.parse_product)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//div[@id="drop_menu"]//ul[@id!="chairs"]//a/@href').extract()
        for cat_url in categories:
            url = urljoin_rfc(base_url, cat_url)
            yield Request(url, callback=self.parse_list)

    def parse_list(self, response):
        hxs = HtmlXPathSelector(response)

        found = False
        for url in hxs.select('//div[@id="product_results"]//a[@class="item_mask"]/@href').extract():
            found = True
            yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_product)
        if found:
            try:
                page = int(response.url.split('/')[-1].replace('pg', ''))
                yield Request(response.url[:response.url.rindex('/') + 1] + 'pg' + str(page + 1), callback=self.parse_list)
            except:
                yield Request(response.url + '/pg2', callback=self.parse_list)


    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('sku', '//input[@id="txtEMLNEID"]/@value')
        loader.add_value('identifier', ':'.join(hxs.select('//input[@id="txtEMLNEID"]/@value').extract() + hxs.select('//input[@id="txtEMSZEID"]/@value').extract()))
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1/text()')
        loader.add_xpath('price', '//div[@id="net"]/text()')
        loader.add_xpath('category', '//div[@id="bread_crumb"]/a[3]/text()')

        img = hxs.select('//img[@id="product_image"]/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        brand = ''.join(hxs.select('//img[contains(@src, "/brands/")]/@src').extract())
        loader.add_value('brand', brand.split('/')[-1].split('.')[0].replace('-', ' '))

        if loader.get_output_value('price'):
            loader.add_value('stock', '1')
        else:
            loader.add_value('stock', '0')

        size = ''.join(hxs.select('normalize-space(//select[@onchange="jump(this.value)"]//option[@selected="selected"]/text())').extract())
        loader.add_value('name', '-'.join(size.split('-')[:-1]))

        price_adj = {}
        for cfg in re.findall('adjustment\((\d+),(\d+),([\d.,]+)\)', response.body):
            price_adj[(cfg[0], cfg[1])] = float(cfg[2])

        # Include only options that change the price
        opt_groups = []
        for sel in hxs.select('//select[@onchange!="jump(this.value)" and @id!="quantity"]'):
            try: id = sel.select('./@id').re('\d+')[0]
            except: continue
            opts = []
            for opt in sel.select('.//option'):

                value = opt.select('./@value').extract()[0]
                text = opt.select('normalize-space(./text())').extract()[0]
                if (id, value) in price_adj and float(price_adj[id, value]) != 0.0:
                    opts.append((price_adj[id, value], text, value))
            if opts:
                opt_groups.append(opts)

        prod = loader.load_item()
        if prod.get('identifier'):
            if response.url in self.SKIP_OPTIONS or not loader.get_output_value('price'):
                yield prod
            else:
                yield prod
                for opt_price, opt_name, opt_id in multiply(opt_groups):
                    p = Product(prod)
                    p['name'] = p['name'] + ' ' + opt_name
                    p['price'] = p['price'] + Decimal(opt_price).quantize(Decimal('1.00'))
                    p['identifier'] = p['identifier'] + ':' + opt_id if opt_id else p['identifier'] + '-'
                    yield p

        for url in hxs.select('//select[@onchange="jump(this.value)"]//option/@value').extract():
            yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_product)
