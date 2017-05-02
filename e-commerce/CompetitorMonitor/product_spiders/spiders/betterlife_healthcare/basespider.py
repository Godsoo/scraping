import re
import json

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.utils import extract_price

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)

class BaseEbaySpider(BaseSpider):
    allowed_domains = ['ebay.co.uk', 'stores.ebay.co.uk']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        next_page = hxs.select('//table[@class="pager"]//td[@class="next"]/a[1]/@href').extract()
        if not next_page:
            next_page = hxs.select('//a[contains(@class, "nextBtn")]/@href').extract()

        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]))

        item_urls = set(hxs.select('//a[@itemprop="url" or @itemprop="name" or @class="vi-url"]/@href').extract())

        for item_url in item_urls:
            yield Request(item_url, callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        if hxs.select('//div[@id="ResultSetItems"]'):
            for x in self.parse(response):
                yield x
            return
            

        first_name = ' '.join(hxs.select('//*[@id="itemTitle"]/text()')
                              .extract()).strip()
        if not first_name:
            return

        identifier = response.url.split('?')[0].split('/')[-1]

        try:
            category = hxs.select('//*[@id="vi-VR-brumb-lnkLst"]//a/text()').extract().pop()
        except:
            category = ''
        seller_id = ''.join(hxs.select('.//*[@class="si-content"]'
                                        '//a/*[@class="mbg-nw"]/text()').extract())
        try:
            brand = hxs.select('//*[@class="attrLabels" and contains(text(), "Brand")]'
                               '/following-sibling::*/text()').extract()[0].strip()
        except:
            brand = ''

        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('name', first_name)
        product_loader.add_value('identifier', identifier)
        product_loader.add_value('category', category)
        product_loader.add_value('dealer', 'eBay - ' + seller_id)
        product_loader.add_value('brand', brand)
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

        options_variations = []
        
        sel = HtmlXPathSelector(text=response.body.replace('&quot;', ''))
        try:
            json_var_map = unicode(sel.select('//*/text()')
                                   .re(r'("menuItemMap":{.*}.*),'
                                       '"unavailableVariationIds"')[0])
        except:
            pass
        else:
            #json_var_map = re.sub(r',"watchCountMessage":".*?}', '}', json_var_map)
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
