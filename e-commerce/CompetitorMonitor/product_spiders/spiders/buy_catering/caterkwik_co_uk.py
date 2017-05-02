import re
import json
import urlparse
from decimal import Decimal
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.base_spiders.prodcache import ProductCacheSpider

class CaterKwikSpider(ProductCacheSpider):
    name = 'buycatering-caterkwik.co.uk'
    allowed_domains = ['caterkwik.co.uk']
    start_urls = ('http://www.caterkwik.co.uk/',)

    def _start_requests(self):
        yield Request('http://www.caterkwik.co.uk/cgi-bin/trolleyed_public.cgi?action=showprod_DCSB40036242', callback=self.parse_product, meta={'product': Product()})
#        http://www.caterkwik.co.uk/cgi-bin/trolleyed_public.cgi?action=showprod_ROBOTCOUPEC200
#        yield Request('http://www.caterkwik.co.uk/cgi-bin/trolleyed_public.cgi?action=showprod_CK0659BBQ', callback=self.parse_product, meta={'product': Product()})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select('//ul[@id="leftnav"]/li[position()>1]/a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_cat)

    def parse_cat(self, response):
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//li[@class="grid-link"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_cat)

        for productxs in hxs.select('//div[contains(@class,"productbox")]'):
            product = Product()
            product['price'] = extract_price(''.join(productxs.select('.//p[@class="product_price"]/strong/text()').extract()))
            if product['price']:
                product['stock'] = 1
            else:
                product['stock'] = 0

            try:
                meta = dict(response.meta)
                meta['product'] = product
                yield Request(urljoin_rfc(get_base_url(response), productxs.select('.//a[@class="info_btn"]/@href').extract()[0]),
                        callback=self.parse_product,
                        meta=meta)
            except IndexError:
                continue

        for url in hxs.select('//div[@class="pages"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_cat, meta=response.meta)

    def parse_product(self, response):
        body = unicode(re.sub(u'(<select|SELECT .*>)</p>', '\\1', response.body), "utf8", errors="ignore")
        hxs = HtmlXPathSelector(text=body)
        loader = ProductLoader(item=response.meta['product'], selector=hxs)
        loader.add_xpath('identifier', '//input[@name="prodid"]/@value')
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//*[@itemprop="name"]//text()')
        loader.add_xpath('sku', '//p/strong[contains(text(), "MPN:")]/../text()')

        loader.add_xpath('category', '//div[@itemprop="breadcrumb"]/a[2]/text()')

        img = hxs.select('//div[contains(@class, "product-image-main")]//img/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        loader.add_xpath('brand', 'normalize-space(//p/strong[contains(text(), "BRAND:")]/../text())')

        got_options = False
        prod = loader.load_item()
        for select in hxs.select('//select[@name and @name!="Accessories" and not(contains(option/@value, "No Thanks"))]'):
            for o in select.select(u'./option'):
                option = ''.join(o.select('.//text()').extract())
                try:
                    name, price = option.split('(')
                except:
                    name, price = option, ''

                if not price or price.startswith('+'):
                    continue

                opt_id = o.select('./@value').extract()[0].split('(')[0].replace(' ', '')
                name = select.select('./@name').extract()[0] + '=' + name
                price = extract_price(price)
                if price == 0:
                    continue

                # Only "options" that are model
                got_options = True
                p = Product(prod)
                p['name'] = p['name'] + ' ' + name
                p['price'] = Decimal(price).quantize(Decimal('1.00'))
                p['identifier'] = p['identifier'] + ':' + opt_id if opt_id else p['identifier']
                yield self.add_shipping_cost(p)

        if not got_options:
            yield self.add_shipping_cost(prod)

    def add_shipping_cost(self, item):
        # Shipping costs can only be found when in checkout. Also depends on the weight of the product. Please just ignore this field
        return item
