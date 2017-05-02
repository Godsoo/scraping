import re
import urllib

from decimal import Decimal
# from scrapy.spider import BaseSpider
from product_spiders.base_spiders.bigsitemethodspider import BigSiteMethodSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy import log

from product_spiders.utils import extract_price

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

def multiply(lst):
    if not lst:
        return [('', 0)]

    while len(lst) > 1:

        # XXX Too many options for http://www.bike24.net/1.php?content=8;navigation=1;product=6233;page=2;menu=1000,173,207;mid=0;pgc=0
        if len(lst[0]) > 1000:
            return [('', 0)]

        result = []
        for name0, price0 in lst[0]:
            for name1, price1 in lst[1]:
                result.append((name0 + ' ' + name1, float(price0) + float(price1)))
        lst = [result] + lst[2:]
    # Dynamic list
    if not lst[0]:
        return [('', 0)]
    return lst[0]

class Bike24NetSpider(BigSiteMethodSpider):
    name = 'bike24.net'
    allowed_domains = ['bike24.net', 'www.bike24.net', 'bike24.de', 'www.bike24.de']
    start_urls = ('http://www.bike24.de/1.php?content=19;navigation=1;mid=0;pgc=0;menu=998',)
    seen_products = set()

    # download_delay = 5

    website_id = 481327
    full_crawl_day = 4

    def parse_full(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        for url in hxs.select('//td[@align="left"]/b/a[@class="bluebold"]/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

        for url in hxs.select('//td[@align="left"]/a[@class="bluebold"]/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_full)


        '''
        for url in hxs.select(u'//table/tr/td/img[@alt="Produktkatalog"]/../../..//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            if 'navigation=2' in url: continue
            yield Request(url, callback=self.parse_full)

        for url in hxs.select(u'//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            if 'navigation=2' in url: continue
            if 'product=' in url:
                product_id = re.search('product=([\d]+)', url).groups()[0]
                if product_id not in self.seen_products:
                    self.seen_products.add(product_id)
                    yield Request(url, callback=self.parse_product)

        for url in hxs.select('//a[@class="contentbold"]/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            if 'page=' in url:
                yield Request(url, callback=self.parse_full)
        '''

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        product_loader = ProductLoader(item=Product(), selector=hxs)


        product_loader.add_xpath('name', u'//h1/text()')
        price = hxs.select(u'//span[@class="price"]/text()').extract()[0]
        product_loader.add_value('price', price.replace('.', '').replace(',', '.'))

        product_loader.add_xpath('sku', u'//input[@name="product"]/@value')
        product_loader.add_xpath('identifier', u'//input[@name="product"]/@value')
        identifier = product_loader.get_output_value('identifier')
        product_loader.add_value('url', 'http://www.bike24.de/p1%s.html' % identifier)
        menu = hxs.select(u'//input[@name="menu"]/@value').extract()[0]
        menu = menu.split(',')[0]
        product_loader.add_xpath('category', u'//img[@id="b%s"]/@alt' % (menu))

        product_loader.add_xpath('image_url', u'//img[@class="cloud-zoom-preview"]/@src')
        js = ''.join(hxs.select(u'//script/text()').extract())
        product_loader.add_xpath('brand', u'//img[@class="pd-description-border"]/@alt')
#            product_loader.add_xpath('shipping_cost', '')
        product = product_loader.load_item()

        opt_groups = []
        def fix_options(o):
            try:
                return (o[0].strip(),
                        re.search('([\d\.,]+)', o[1]).groups()[0].replace('.', '').replace(',', '.'))
            except:
                return (o[0].strip(), '0')

        for option in hxs.select(u'//select[@class="selectbox"]'):
            opt_list = option.select(u'./option[@value != "-2"]/text()').extract()
            opt_list = [o.split('Aufpreis') for o in opt_list]
            opt_groups.append([fix_options(o) for o in opt_list])

        options = hxs.select(u'//select[@class="selectbox"]/option[@value != "-2"]/text()').extract()
        if options:
            for (opt_name, opt_price) in multiply(opt_groups):
                prod = Product(product)
                prod['name'] = prod['name'] + ' ' + opt_name
                prod['price'] = prod['price'] + Decimal(opt_price)
                prod['identifier'] = prod['identifier'] + '_' + ''.join(opt_name.lower().split())
                yield prod
        else:
            yield product
