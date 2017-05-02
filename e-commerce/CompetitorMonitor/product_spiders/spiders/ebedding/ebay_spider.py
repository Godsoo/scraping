import os
import re
import csv
import json

from scrapy import Spider

from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.utils import extract_price

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)

from urlparse import urljoin
from urllib import urlencode


HERE = os.path.abspath(os.path.dirname(__file__))

class EbeddingeBaySpider(Spider):
    name = 'ebedding-ebay.co.uk'
    allowed_domains = ['stores.ebay.co.uk', 'ebay.co.uk']
    new_products_only = True
    start_urls = ['http://www.ebay.co.uk']

    collect_stock = True

    filename = os.path.join(HERE, 'ebedding_products.csv')

    def parse(self, response):
        base_url = get_base_url(response)
        
        with open(self.filename) as f:
            reader = csv.DictReader(f)
            for row in reader:
                search_url = self._get_url_search(row['EAN'])
                yield Request(search_url, callback=self.parse_products, meta={'row': row})

    def parse_products(self, response):

        items = response.xpath('//div[@id="ResultSetItems"]//h3/a/@href').extract()
        for item in items:
            yield Request(item, callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):

        row = response.meta['row']

        if response.xpath('//div[@id="ResultSetItems"]'):
            for x in self.parse(response):
                yield x
            return
            
        if self.new_products_only:
            condition_new = response.xpath('//div[@id="vi-itm-cond" and contains(text(), "New")]')
            if not condition_new:
                return

        first_name = ' '.join(response.xpath('//*[@id="itemTitle"]/text()')
                              .extract()).strip()
        if not first_name:
            return

        identifier = response.url.split('?')[0].split('/')[-1]

        try:
            category = response.xpath('//td[contains(@class, "brumblnkLst")]//li/a/text()').extract()
        except:
            category = ''
        
        brand = response.xpath('//td[contains(text(), "Brand:")]/following-sibling::td[1]/span/text()').extract()
        brand = brand[0] if brand else ''

        sku = row['EAN']

        seller_id = ''.join(response.xpath('.//*[contains(@class, "si-content")]'
                                        '//a/*[@class="mbg-nw"]/text()').extract())

        dealer = 'eBay - ' + seller_id if seller_id else ''

        product_loader = ProductLoader(item=Product(), response=response)
        product_loader.add_value('name', first_name)
        product_loader.add_value('identifier', identifier)
        product_loader.add_value('category', category)
        product_loader.add_value('brand', brand)
        product_loader.add_value('dealer', dealer)
        product_loader.add_value('sku', sku)
        delisted = response.xpath('//span[@class="msgTextAlign" and contains(text(),"This listing was ended by the seller because the item is no longer available.")]')
        if delisted:
            return
        if self.collect_stock:
            stock = response.xpath('//span[@id="qtySubTxt"]/span[contains(text(), "Last one")]')
            stock = 1 if stock else 0
            if stock:
                product_loader.add_value('stock', stock)
            else:
                stock = response.xpath('//span[@id="qtySubTxt"]/span/text()').re('\d+')
                if stock:
                    stock = int(stock[0])
                    product_loader.add_value('stock', stock)

        product_loader.add_xpath('image_url', '//img[@id="icImg"]/@src')
        product_loader.add_value('url', response.url)
        try:
            price = response.xpath('//*[@id="prcIsum"]/text()').extract()[0].strip()
        except:
            try:
                price = response.xpath('//*[@id="mm-saleDscPrc"]/text()').extract()[0].strip()
            except:
                try:
                    price = re.search(r'"binPrice":".*([\d\.,]+)",', response.body).groups()[0]
                except:
                    price = re.search(r'"bidPrice":".*([\d\.,]+)",', response.body).groups()[0]
        product_loader.add_value('price', extract_price(price))

        # shipping cost
        try:
            shipping_cost = response.xpath('//*[@id="shippingSection"]//td/div/text()').extract()[0]
            if shipping_cost:
                if 'free' in shipping_cost.lower():
                    product_loader.add_value('shipping_cost', 0)
                else:
                    product_loader.add_value('shipping_cost', extract_price(shipping_cost))
        except:
            pass

        product_ = product_loader.load_item()

        #ean = response.xpath('//td[contains(text(), "EAN:")]/following-sibling::td[1]/span/text()').extract()

        options_variations = []

        try:
            json_var_map = unicode(response.xpath('//*/text()')
                                   .re(r'("menuItemMap":{.*}.*),'
                                       '"unavailableVariationIds"')[0])
        except:
            pass
        else:
            try:
                json_var_map_fixed = re.sub(r',"watchCountMessage":".*?}', '}', json_var_map)
                variations = json.loads('{' + re.sub(r',"unavailableVariationIds".*', '', json_var_map_fixed) + '}')
            except ValueError:
                try:
                    json_var_map_fixed = re.sub(r',"watchCountMessage":".*?,', ',', json_var_map)
                    variations = json.loads('{' + re.sub(r',"unavailableVariationIds".*', '', json_var_map_fixed) + '}')
                except ValueError:
                    retry = response.meta.get('retry', 1)
                    if retry <=3:
                        meta = response.meta
                        meta['retry'] = retry + 1
                        yield Request(response.url, dont_filter=True, callback=self.parse_product, meta=meta)
                    return

            menu_map = variations['menuItemMap']

            try:
                item_variations = variations['itemVariationsMap'].items()
                for key, variation in item_variations:
                    if variation['traitValuesMap']:
                        new_variation = {}
                        for option, value in variation['traitValuesMap'].items():
                            new_variation[option] = menu_map[str(value)]['displayName']
                    
                        price = variation['price'] if variation.get('price', None) else variation.get('convertedPrice', None)

                        # if price = 0 raise an exception to retry the page
                        if not price and response.meta.get('retry', 1)<=5:
                            self.log('>>> Price 0, reload page to extract correct price: ' + response.url)
                            raise ValueError
                        options_variations.append({'price': price,
                                                   'stock': variation['quantityAvailable'],
                                                   'values': new_variation,
                                                   'identifier': '%s:%s' % (identifier, key)})
            except (KeyError, ValueError):
                retry = response.meta.get('retry', 1)
                if retry <=5:
                    meta = response.meta
                    meta['retry'] = retry + 1
                    yield Request(response.url, dont_filter=True, callback=self.parse_product, meta=meta)
                return

        if options_variations:
            for model in options_variations:
                model_name = first_name + ' ' + \
                    ' '.join(opt_name.strip().lower()
                             for o, opt_name in model['values'].items())
                new_product = Product(product_)
                new_product['name'] = model_name
                new_product['stock'] = model['stock']
                new_product['identifier'] = model['identifier']
                new_product['price'] = extract_price(model['price'])

                yield new_product
        else:
            yield product_

    def _get_url_search(self, search):
        params = {'_sop': '2',
                  '_fss': '1',
                  '_rusck': '1',
                  '_sacat': '0',
                  '_from': 'R40',
                  'LH_BIN': '1',
                  'LH_ItemCondition': '3',
                  'rt': 'nc',
                  '_nkw': search,
                  '_odkw': search}

        url = urljoin('http://www.ebay.co.uk/', 'dsc/i.html?%(params)s' %
                          ({'params': urlencode(params)}))
        url = url + '&_fcid=3&_localstpos&_stpos&gbr=1'
        return url
