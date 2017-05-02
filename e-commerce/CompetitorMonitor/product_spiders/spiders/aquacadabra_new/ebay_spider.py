import os
import re
import csv
import json

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse


from product_spiders.base_spiders import BaseeBaySpider

from product_spiders.utils import extract_price

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)

HERE = os.path.abspath(os.path.dirname(__file__))


class AquacadabraEbaySpider(BaseeBaySpider):

    HERE = os.path.abspath(os.path.dirname(__file__))

    name = 'aquacadabra-ebay.co.uk'

    def __init__(self, *args, **kwargs):
        super(AquacadabraEbaySpider, self).__init__()
        self._csv_file = os.path.join(self.HERE, 'aquacadabra_products.csv')
        self._converted_price = True
        self._ebay_url = 'http://www.ebay.co.uk'
        self._search_fields = ['sku']
        self._all_vendors = True
        self._look_related = True
        self._look_related_not_items = True
        self.new_products_only = False
        self.collect_stock = True

        self._check_valid_item = self._valid_item_

    def start_requests(self):
        number = 0
        with open(self._csv_file) as f:
            reader = csv.DictReader(f, delimiter=',')
            for row in reader:
                number += 1
                meta = {
                    'sku': row['SKU']
                }

                search = ' '.join(meta[field].strip() for field in self._search_fields)
                meta.update({'search': search})
                # Get URL
                search = self._clean_search(search)  # Clean search
                url = self._get_url_search(search)
                self.log('Item %s | Search by: %s' % (number, search))
                yield self._search(url, meta)

    def parse_product(self, response):
        meta = response.meta['item_meta'].copy()
        sku = meta.get('sku', '')

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
        delisted = response.xpath(
            '//span[@class="msgTextAlign" and contains(text(),"This listing was ended by the seller because the item is no longer available.")]')
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

        # ean = response.xpath('//td[contains(text(), "EAN:")]/following-sibling::td[1]/span/text()').extract()

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
                    if retry <= 3:
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

                        price = variation['price'] if variation.get('price', None) else variation.get('convertedPrice',
                                                                                                      None)

                        # if price = 0 raise an exception to retry the page
                        if not price and response.meta.get('retry', 1) <= 5:
                            self.log('>>> Price 0, reload page to extract correct price: ' + response.url)
                            raise ValueError
                        options_variations.append({'price': price,
                                                   'stock': variation['quantityAvailable'],
                                                   'values': new_variation,
                                                   'identifier': '%s:%s' % (identifier, key)})
            except (KeyError, ValueError):
                retry = response.meta.get('retry', 1)
                if retry <= 5:
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

    def load_item(self, *args, **kwargs):
        product_loader = super(AquacadabraEbaySpider, self).load_item(*args, **kwargs)

        response = args[-1]

        hxs = HtmlXPathSelector(response=response)
        categories = hxs.select('//ul[contains(@itemtype,"Breadcrumblist")]//span/text()').extract()
        product_loader.replace_value('category', categories)
        return product_loader

    def _valid_item_(self, item_loader, response):
        return True

