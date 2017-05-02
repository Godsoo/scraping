# -*- coding: utf-8 -*-
from decimal import Decimal

from scrapy.selector import HtmlXPathSelector
from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from product_spiders.utils import extract_price

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

def multiply(lst):
    if not lst:
        return [(0, '', '')]

    while len(lst) > 1:
        result = []
        for price0, name0, id0 in lst[0]:
            for price1, name1, id1 in lst[1]:
                result.append((float(price0) + float(price1),
                               name0 + ' ' + name1,
                               id0.replace(',', ':') + ':' + id1.replace(',', ':')))
        lst = [result] + lst[2:]
    return lst[0]

class MattressOnlineCoUkSpider(BaseSpider):
    name = "colourbank-mattressonline.co.uk"
    allowed_domains = ('mattressonline.co.uk', )
    start_urls = ('http://www.mattressonline.co.uk/', )

    def start_requests(self):
        yield Request('http://www.mattressonline.co.uk/', callback=self.parse_full)

    def parse_full(self, response):
        hxs = HtmlXPathSelector(response)

        for li in hxs.select(u'//div[@id="vertical-nav"]//ul/ul/li'):
            for url in li.select(u'.//a/@href').extract():
                url = urljoin_rfc(get_base_url(response), url)
                yield Request(url, callback=self.parse_product_list,
                        meta={'category':li.select(u'normalize-space(./a/text())').extract()[0]})

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select(u'//div[@class="sub-categories"]//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product_list, meta=response.meta)

        for url in hxs.select(u'//div[contains(@class,"paging")]/div[@class="controls"]//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product_list, meta=response.meta)

        for url in hxs.select(u'//div[contains(@class,"product-item")]//h3/a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('url', response.url)
        product_loader.add_xpath('name', u'//h1/text()')
        product_loader.add_value('category', response.meta.get('category'))

        img = hxs.select(u'//img[@id="gallery-image"]/@src').extract()
        if img:
            product_loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        product_loader.add_xpath('brand', u'//div[@class="manufacturer-logo"]/a/img/@alt')

        product = product_loader.load_item()
        for opt in hxs.select(u'//div[contains(@class,"purchase-options")]/div/form'):
            prod = Product(product)
            prod['name'] = prod['name'] + ' ' + opt.select(u'.//span[@class="option"]/text()').extract()[0].strip()
            prod['price'] = extract_price(opt.select(u'.//input[contains(@id, "-base-sale-price")]/@value').extract()[0])
            prod['sku'] = opt.select(u'.//input[@name="product-id"]/@value').extract()[0]
            prod['identifier'] = opt.select(u'.//input[@name="product-id"]/@value').extract()[0]

            opt_groups = []
            for select in opt.select(u'.//select/../../label[not(contains(text(),"Delivery"))]/../div/select'):
                opts = []
                import logging
                for o in select.select(u'./option[not(contains(text(), "None"))]'):
                    option = ''.join(o.select('.//text()').extract())
                    id = o.select('./@value').extract()[0]
                    try:
                        logging.error(option)
                        name, price = option.split('(')
                        price = extract_price(price)
                    except:
                        name, price = option, 0
                    opts.append((price, name, id))
                opt_groups.append(opts)

            for opt_price, opt_name, opt_id in multiply(opt_groups):
                p = Product(prod)
                p['name'] = p['name'] + ' ' + opt_name
                p['price'] = p['price'] + Decimal(opt_price).quantize(Decimal('1.00'))
                p['identifier'] = p['identifier'] + ':' + opt_id if opt_id else p['identifier'] + '-'
                yield p
