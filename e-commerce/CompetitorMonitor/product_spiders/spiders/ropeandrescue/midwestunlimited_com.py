import re
import logging

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from utils import extract_price


class MidWestUnlimitedComSpider(BaseSpider):
    name = 'midwestunlimited.com'
    allowed_domains = ['midwestunlimited.com']
    start_urls = ('http://www.midwestunlimited.com',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select(u'//div[contains(@class,"nav_categories")]/ul/li/a/@href').extract():
            yield Request(url, callback=self.parse_product_list)

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)

        cats = hxs.select(u'//ul[contains(@class,"ProductGroups")]/li/div[1]/a/@href').extract()

        for url in cats:
            yield Request(url, callback=self.parse_product_list)

        products = hxs.select(u'//div[contains(@class,"ProductTitle")]//a/@href').extract()

        for url in products:
            yield Request(url, callback=self.parse_product)

        next_url = hxs.select(u'//div[contains(@class,"CategoryPagination")]/span/a[contains(text(),"Next")]/@href').extract()

        if next_url:
            yield Request(next_url[0], callback=self.parse_product_list)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('url', response.url)
        product_loader.add_xpath('name', u'//h2/text()')
        product_loader.add_xpath('price', u'//em[contains(@class,"ProductPrice")]/text()')
        product_loader.add_xpath('sku', u'//span[@class="VariationProductSKU"]/text()')
        product_loader.add_xpath('identifier', '//form/input[@name="product_id"]/@value')
        product_loader.add_xpath('category', u'//div[@id="ProductBreadcrumb"]/ul/ul/li[2]/a/text()')
        product_loader.add_xpath('image_url', u'//div[@class="ProductThumbImage"]/a/img/@src')
        product_loader.add_xpath('brand', u'//div[@class="Value"]/a/text()')
        product_loader.add_value('shipping_cost', '')

        # options = hxs.select(u'//div[@class="DetailRow"]//ul/li/label/input/../..')
        options = hxs.select(u'//div[@class="DetailRow"]/div[@class="Value"]/table/tr/td/input/../..')
        if options:

            product_id = hxs.select(u'//input[@name="product_id"]/@value').extract()[0]

            product_orig = product_loader.load_item()

            for opt_tr in options:

                option_name_lst = opt_tr.select(u'.//input/../../td[position()>1]/text()').extract()

                option_name_lst = [x.strip() for x in option_name_lst]

                option_name = " ".join(option_name_lst)
                option_name = re.sub(' +', ' ', option_name)

                # name = opt.select(u'.//input/../text()[2]').extract()
                if not option_name:
                    self.log("ERROR option name is empty")
                    continue
                    # name = opt.select(u'concat(.//input/../span[1]/text(),.//input/../span[2]/text())').extract()

                var = opt_tr.select(u'.//input/@value').extract()

                if not var:
                    self.log("ERROR option var is empty")
                    continue

                cur_product = Product(product_orig)
                cur_product['name'] = (cur_product['name'] + ' ' + option_name).strip()
                yield Request('http://www.midwestunlimited.com/remote.php' +
                        '?w=GetVariationOptions&productId=' + product_id + '&options=' + var[0],
                        meta={'product': cur_product, 'options': var[0]}, callback=self.parse_price)
        else:
            yield product_loader.load_item()

    def parse_price(self, response):

        product = response.meta['product']

        # data = eval(response.body, {'true':True, 'false':False})

        import json
        try:
            data = json.loads(response.body)
        except:
            self.log("ERROR cant load json, response.body=" + response.body)
            return

        if 'price' in data:
            product['price'] = extract_price(data['price'])

        if 'sku' in data and data['sku']:
            product['sku'] = data['sku']

        product['identifier'] = product['identifier'] + '_' + response.meta['options']

        if 'image' in data and data['image']:
            product['image_url'] = data['image'].replace('\\', '')
        elif 'thumb' in data and data['thumb']:
            product['image_url'] = data['thumb'].replace('\\', '')

        yield product
