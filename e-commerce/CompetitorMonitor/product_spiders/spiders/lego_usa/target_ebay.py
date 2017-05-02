from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price
from scrapy.http import Request
import re
import json

from scrapy import log


class TargetEbayLegoUSASpider(BaseSpider):
    name = 'legousa-target-ebay.com'
    allowed_domains = ['ebay.com']
    start_urls = ('http://stores.ebay.com/Target-Store/_i.html?_dmd=2&_nkw=lego&rt=nc&_ipg=192',)

    rotate_agent = True

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = hxs.select('//div[@class="wp"]//div[@class="title"]/a/@href').extract()
        products += hxs.select('//div[contains(@class, "item-cell")]//div[@class="desc"]/a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

        pages = hxs.select('//*[@id="pager"]//a[@class="no"]/@href').extract()
        pages += hxs.select('//*[@class="tppng"]//a/@href').extract()
        for url in pages:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        name = ' '.join(hxs.select('//*[@id="itemTitle"]/text()').extract()).strip()
        identifier = response.url.split('?')[0].split('/')[-1]
        sku = ''
        for match in re.finditer(r"([\d,\.]+)", name):
            if len(match.group()) > len(sku):
                sku = match.group()
        brand = 'Lego'

        price = None
        try:
            price = hxs.select('//*[@id="prcIsum"]/text()').extract()[0].strip()
        except IndexError:
            try:
                price = hxs.select('//*[@id="mm-saleDscPrc"]/text()').extract()[0].strip()
            except IndexError:
                try:
                    price = re.search(r'"binPrice":".*[\$\xA3]([\d\.,]+)",', response.body).groups()[0]
                except AttributeError:
                    self.log("Price not found for " + response.url)

        image_url = hxs.select('//img[@id="icImg"]/@src').extract()
        category = 'Lego'

        # shipping cost
        shipping_cost = None
        try:
            shipping_cost = hxs.select('//*[@id="shippingSection"]//td/div/text()').extract()[0]
            if shipping_cost:
                if 'free' in shipping_cost.lower():
                    shipping_cost = 0
                else:
                    shipping_cost = extract_price(shipping_cost)
        except IndexError:
            pass

        options_variations = []

        try:
            json_var_map = unicode(hxs.select('//*/text()')
                                   .re(r'("menuItemMap":{.*}.*),'
                                       '"unavailableVariationIds"')[0])
        except:
            self.log('No item variations map...')
        else:
            json_var_map = re.sub(r',"watchCountMessage":".*?}', '}', json_var_map)
            variations = json.loads('{' + re.sub(r',"unavailableVariationIds".*', '', json_var_map) + '}')

            menu_map = variations['menuItemMap']

            for key, variation in variations['itemVariationsMap'].items():
                if variation['traitValuesMap']:
                    new_variation = {}
                    for option, value in variation['traitValuesMap'].items():
                        new_variation[option] = menu_map[str(value)]['displayName']
                    price = variation['price']
                    options_variations.append({'price': price,
                                               'values': new_variation,
                                               'identifier': key})

        if options_variations:
            for product in options_variations:
                product_loader = ProductLoader(item=Product(), selector=product)
                p_name = name + ' ' + \
                    ' '.join(opt_name.strip().lower()
                             for o, opt_name in product['values'].items())
                p_identifier = product['identifier']
                price = product['price']
                price = extract_price(price)
                product_loader.add_value('identifier', identifier + '_' + p_identifier)
                product_loader.add_value('name', p_name)
                product_loader.add_value('sku', sku)
                if image_url:
                    product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
                product_loader.add_value('price', price)
                product_loader.add_value('category', category)
                product_loader.add_value('brand', brand)
                product_loader.add_value('url', response.url)
                if shipping_cost is not None:
                    product_loader.add_value('shipping_cost', shipping_cost)
                product = product_loader.load_item()
                yield product
        else:
            product_loader = ProductLoader(item=Product(), selector=hxs)
            price = extract_price(price)
            product_loader.add_value('identifier', identifier)
            product_loader.add_value('name', name)
            product_loader.add_value('sku', sku)
            if image_url:
                product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            product_loader.add_value('price', price)
            product_loader.add_value('category', category)
            product_loader.add_value('brand', brand)
            product_loader.add_value('url', response.url)
            if shipping_cost is not None:
                    product_loader.add_value('shipping_cost', shipping_cost)
            product = product_loader.load_item()
            yield product
