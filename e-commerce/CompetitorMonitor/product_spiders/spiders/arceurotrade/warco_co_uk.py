import re
from decimal import Decimal
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class WarcoCoUkSpider(BaseSpider):
    name = 'warco.co.uk'
    allowed_domains = ['warco.co.uk']

    def __init__(self, *args, **kwargs):
        super(WarcoCoUkSpider, self).__init__(*args, **kwargs)
 
    def start_requests(self):
        yield Request('http://warco.co.uk/', callback=self.parse_full)

    def parse_full(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select(u'//div[@id="categories_block_left"]//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product_list)

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select(u'//ul[@id="product_list"]//h3/a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product, meta=response.meta)

        for url in hxs.select(u'//li[@id="pagination_next"]/a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product_list, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('url', response.url)
        product_loader.add_xpath('name', u'//div[@id="primary_block"]/h2/text()')
        # inc. vat
        product_loader.add_xpath('price', u'//span[@id="our_price_display"]/text()')
        product_loader.add_xpath('category', u'//span[@class="navigation_end"]/a[1]/text()')

        img = hxs.select(u'//img[@id="bigpic"]/@src').extract()[0]
        product_loader.add_value('image_url', urljoin_rfc(get_base_url(response), img))

        product_loader.add_xpath('sku', u'//p[@id="product_reference"]/span/text()')
        product_loader.add_xpath('identifier', u'//p[@id="product_reference"]/span/text()')
#product_loader.add_xpath('brand', '')
#product_loader.add_xpath('shipping_cost', '')

        opt_data = {}
        for line in response.body.split('\n'):
            m = re.search('addCombination\(.*, new Array\(\'(.*)\'\), .*, (.*), .*, (.*), \'(.*)\'\);', line)
            if m:
                g = m.groups()
                # option id, price adj, img code, sku
                opt_data[g[0]] = (Decimal(g[1]), g[2], g[3])

        product = product_loader.load_item()

        options = hxs.select(u'//div[@id="attributes"]//option')
        if options:
            value = hxs.select(u'//div[@id="attributes"]//option[@selected]/@value').extract()[0]
            base_price = product['price'] - opt_data[value][0]
            for opt in options:
                value = opt.select(u'./@value').extract()[0]
                text = opt.select(u'normalize-space(./text())').extract()[0]

                prod = Product(product)
                prod['name'] = prod['name'] + ' ' + text
                prod['sku'] = opt_data[value][2]
                prod['identifier'] = opt_data[value][2]
                prod['price'] = base_price + opt_data[value][0]
                img_parts = prod['image_url'].split('-')
                if opt_data[value][1] != '-1':
                    img_parts[1] = opt_data[value][1]
                prod['image_url'] = '-'.join(img_parts)
                yield prod
        else:
            yield product
