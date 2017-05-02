import re
import json

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from getinthemixitem import GetInTheMixMeta

from product_spiders.utils import extract_price

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)

class BaseGetInTheMixEBaySpider(BaseSpider):
    allowed_domains = ['stores.ebay.co.uk', 'ebay.co.uk']
    collect_stock = False
    new_products_only = True

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        
        cat_urls = hxs.select('//div[(@class="lcat") or (@id="cats-lp")]//a/@href').extract()
        for cat_url in cat_urls:
            yield Request(urljoin_rfc(base_url, cat_url))

        next_page = hxs.select('//table[@class="pager"]//td[@class="next"]/a[1]/@href').extract()
        if not next_page:
            next_page = hxs.select('//a[contains(@class, "nextBtn")]/@href').extract()

        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]))

        item_urls = hxs.select('//a[@itemprop="url" or @itemprop="name" or @class="vi-url"]/@href').extract()
        item_urls += hxs.select('//div[contains(@class, "item-cell")]//div[@class="title"]/a/@href').extract()
        
        for item_url in item_urls:
            yield Request(item_url, callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        if hxs.select('//div[@id="ResultSetItems"]'):
            for x in self.parse(response):
                yield x
            return
            
        if self.new_products_only:
            condition_new = hxs.select('//div[@id="vi-itm-cond" and contains(text(), "New")]')
            if not condition_new:
                return

        first_name = ' '.join(hxs.select('//*[@id="itemTitle"]/text()')
                              .extract()).strip()
        if not first_name:
            return

        identifier = response.url.split('?')[0].split('/')[-1]

        try:
            category = hxs.select('//td[contains(@class, "brumblnkLst")]//li/a/text()').extract()
        except:
            category = ''
        
        brand = hxs.select('//td[contains(text(), "Brand:")]/following-sibling::td[1]/span/text()').extract()
        brand = brand[0] if brand else ''

        sku = hxs.select('//td[contains(text(), "MPN:")]/following-sibling::td[1]/span/text()').extract()
        sku = sku[0] if sku else ''

        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('name', first_name)
        product_loader.add_value('identifier', identifier)
        product_loader.add_value('category', category)
        product_loader.add_value('brand', brand)
        product_loader.add_value('sku', sku)
        if self.collect_stock:
            stock = hxs.select('//span[@id="qtySubTxt"]/span[contains(text(), "Last one")]')
            stock = 1 if stock else 0
            if stock:
                product_loader.add_value('stock', stock)
            else:
                stock = hxs.select('//span[@id="qtySubTxt"]/span/text()').re('\d+')
                if stock:
                    stock = int(stock[0])
                    product_loader.add_value('stock', stock)

        product_loader.add_xpath('image_url', '//img[@id="icImg"]/@src')
        product_loader.add_value('url', response.url)
        try:
            price = hxs.select('//*[@id="prcIsum"]/text()').extract()[0].strip()
        except:
            try:
                price = hxs.select('//*[@id="mm-saleDscPrc"]/text()').extract()[0].strip()
            except:
                try:
                    price = re.search(r'"binPrice":".*([\d\.,]+)",', response.body).groups()[0]
                except:
                    price = re.search(r'"bidPrice":".*([\d\.,]+)",', response.body).groups()[0]
        product_loader.add_value('price', extract_price(price))

        # shipping cost
        try:
            shipping_cost = hxs.select('//*[@id="shippingSection"]//td/div/text()').extract()[0]
            if shipping_cost:
                if 'free' in shipping_cost.lower():
                    product_loader.add_value('shipping_cost', 0)
                else:
                    product_loader.add_value('shipping_cost', extract_price(shipping_cost))
        except:
            pass

        product_ = product_loader.load_item()

        metadata = GetInTheMixMeta()
        metadata['promotion'] = self.get_promotion_text(hxs)
        ean = hxs.select('//td[contains(text(), "EAN:")]/following-sibling::td[1]/span/text()').extract()
        metadata['ean'] = ean[0] if ean else ''

        product_['metadata'] = metadata


        options_variations = []

        try:
            json_var_map = unicode(hxs.select('//*/text()')
                                   .re(r'("menuItemMap":{.*}.*),'
                                       '"unavailableVariationIds"')[0])
        except:
            pass
        else:
            json_var_map = re.sub(r',"watchCountMessage":".*?}', '}', json_var_map)
            variations = json.loads('{' + re.sub(r',"unavailableVariationIds".*', '', json_var_map) + '}')

            menu_map = variations['menuItemMap']

            for key, variation in variations['itemVariationsMap'].items():
                if variation['traitValuesMap']:
                    new_variation = {}
                    for option, value in variation['traitValuesMap'].items():
                        new_variation[option] = menu_map[str(value)]['displayName']
                    options_variations.append({'price': variation['price'],
                                               'values': new_variation,
                                               'identifier': '%s:%s' % (identifier, key)})

        if options_variations:
            for model in options_variations:
                model_name = first_name + ' ' + \
                    ' '.join(opt_name.strip().lower()
                             for o, opt_name in model['values'].items())
                new_product = Product(product_)
                new_product['name'] = model_name
                new_product['identifier'] = model['identifier']
                new_product['price'] = extract_price(model['price'])

                yield new_product
        else:
            yield product_

    def get_promotion_text(self, hxs):
        promotion = hxs.select('//div[contains(@class, "vi-VR-prcTmt-hide")]//span/text()').extract()
        return ' '.join(map(lambda x: x.strip(), promotion))
