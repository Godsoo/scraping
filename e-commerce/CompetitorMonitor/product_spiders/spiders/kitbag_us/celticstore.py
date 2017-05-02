"""
Original ticket: https://app.assembla.com/spaces/competitormonitor/tickets/4950
Extract all items from the Football kits category
"""

import re
import json
from decimal import Decimal, ROUND_DOWN
from scrapy.spider import BaseSpider
from scrapy.http import Request, FormRequest
from scrapy.utils.url import add_or_replace_parameter
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader

from product_spiders.utils import extract_price


def format_price(price, rounding=None):
    if price is None:
        return Decimal('0.00')

    return price.quantize(Decimal('0.01'), rounding=rounding or ROUND_DOWN)


class CelticSuperStore(BaseSpider):
    name = 'kitbag_us-celticsuperstore.co.uk'
    allowed_domains = ['celticsuperstore.co.uk']
    start_urls = ['http://celticsuperstore.co.uk/stores/celtic/en/c/kits?cur=USD',
                  'http://celticsuperstore.co.uk/stores/celtic/en/c/fashion?cur=USD',
                  'http://celticsuperstore.co.uk/stores/celtic/en/c/retro-shirts?cur=USD',
                  'http://celticsuperstore.co.uk/stores/celtic/en/c/equipment?cur=USD']
    extracted_identifiers = []

    def start_requests(self):
        yield Request('http://celticsuperstore.co.uk/stores/celtic/en/product/celtic-stainless-steel-bike-bottle/170140',
                      callback=self.parse_shipping)

    def parse_shipping(self, response):
        formdata = {}
        formdata['__VIEWSTATEGENERATOR'] = response.xpath('//input[@name="__VIEWSTATEGENERATOR"]/@value').extract()[0]
        formdata['__EVENTVALIDATION'] = response.xpath('//input[@name="__EVENTVALIDATION"]/@value').extract()[0]
        formdata['__VIEWSTATE'] = response.xpath('//input[@name="__VIEWSTATE"]/@value').extract()[0]
        formdata['__EVENTTARGET'] = ''
        formdata['ctl00$ScriptManager1'] = ''
        formdata['ctl00$ContentMain$product_details1$dd_quantity'] = '1'
        formdata['ctl00$ContentMain$product_details1$imgbtn_addToBasket.x'] = '0'
        formdata['ctl00$ContentMain$product_details1$imgbtn_addToBasket.y'] = '0'

        req = FormRequest.from_response(response, formname='aspnetForm', formdata=formdata,
                                        callback=self.parse_shipping1)
        yield req

    def parse_shipping1(self, response):
        req = Request("http://celticsuperstore.co.uk/stores/celtic/en/basket/basket?atb=True&cur=USD", dont_filter=True,
                      callback=self.parse_shipping2)
        yield req

    def parse_shipping2(self, response):
        shipping_cost = response.xpath('//select[contains(@id, "shippingMethods")]/option/text()').re('(\d+\.\d+)')
        try:
            self.shipping_cost = extract_price(shipping_cost[0])
            self.logger.info('Shipping cost is %s' % self.shipping_cost)
        except IndexError:
            self.logger.error('No shipping cost parsed from basket. Spider will be closed')
        for url in self.start_urls:
            yield Request(url)

    def parse(self, response):
        categories = response.xpath('//div[contains(@class,"facetCategory")]//a/@href').extract()
        categories += response.xpath('//a[h3[@class="kbFont"]]/@href').extract()
        for url in categories:
            yield Request(response.urljoin(url))

        show_all = response.xpath('//a[@id="ctl00_ContentMain_product_browse1_lv_pagingTop_lb_viewAll"]')
        if show_all:
            formdata = dict()
            formdata['__VIEWSTATEGENERATOR'] = response.xpath('//input[@name="__VIEWSTATEGENERATOR"]/@value').extract()[0]
            formdata['__EVENTVALIDATION'] = response.xpath('//input[@name="__EVENTVALIDATION"]/@value').extract()[0]
            formdata['__EVENTTARGET'] = 'ctl00$ContentMain$product_browse1$lv_pagingTop$lb_viewAll'
            formdata['ctl00$ScriptManager1'] = ('ctl00$ContentMain$product_browse1$up_Product_Browse|'
                                                'ctl00$ContentMain$product_browse1$lv_pagingTop$lb_viewAll')

            req = FormRequest.from_response(response,
                                            formname='aspnetForm',
                                            formdata=formdata,
                                            dont_filter=True,
                                            meta=response.meta)

            req.headers['User-Agent'] = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:40.0) Gecko/20100101 Firefox/40.0'
            req.headers['X-MicrosoftAjax'] = 'Delta=true'
            req.headers['X-Requested-With'] = 'XMLHttpRequest'
            yield req

        products = response.xpath('//div[@class="productListLink"]//a[contains(@id,"ProductLink")]/@href').extract()
        for url in products:
            url = add_or_replace_parameter(url, 'cur', 'USD')
            yield Request(response.urljoin(url),
                          callback=self.parse_product)

    def parse_product(self, response):
        if 'aspxerrorpath' in response.url:
            yield Request(response.request.meta['redirect_urls'][0], self.parse_product, dont_filter=True)
        base_product = True
        add_custom_personalization = False
        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('url', '//link[@rel="canonical"]/@href')
        loader.add_value('category', 'Kits')
        heros_data = response.xpath('//script/text()').re('product\d{7} =(.+?});var')
        base_product_data = response.xpath('//script/text()').re('product\w{6} =(.+?});var')
        if not base_product_data:
            for p in self.parse(response):
                yield p
            return
        if not heros_data:
            data = json.loads(base_product_data[0])
        elif len(heros_data) == 1:
            data = json.loads(heros_data[0])
            base_product = False
        else:
            data = [json.loads(x) for x in heros_data]
            data = {x['ProductID']: x for x in data}
            heros = response.css('select.heroShirts')
            hero = heros.xpath('option[@selected]')
            if not hero:
                data = json.loads(base_product_data[0])
            else:
                data = data[int(hero.xpath('@value').extract_first())]
                base_product = False
                
        base_product_data = json.loads(base_product_data[0])
        
        #Checking custom personalization
        printings = {p['PrintingTypeID']: p for p in base_product_data['printingitems']}
        custom_printings = printings.get(1)
        if custom_printings and base_product:
            add_custom_personalization = True
            
        loader.add_value('name', data['Description'])
        loader.add_xpath('sku', '//script/text()', re='sku":"(.+?)"')
        if data['Brand']:
            loader.add_value('brand', data['Brand']['Name'])
        loader.add_value('image_url', response.urljoin(data['ImageURL']))
        loader.add_value('shipping_cost', self.shipping_cost)
        product = loader.load_item()
        player_from_name = re.search('(?!Sponsor).*with *([\w\ \.\-]+?) (\d+)', data.get('Description', ''), re.UNICODE)
        if player_from_name:
            player_name, number = player_from_name.groups()
            
        #sizes
        for variation in data['Variations']:
            size = variation['Description']
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value(None, product)
            loader.replace_value('identifier', variation['VariationId'])
            loader.add_value('name', size)
            loader.replace_value('price', variation['PriceActual'])
            loader.replace_value('stock', int(variation['IsInStock']))
            item = loader.load_item()
            if player_from_name:
                item['metadata'] = {'player': player_name, 'number': number, 'size': size}
            else:
                item['metadata'] = {'size': size}
            yield item
            base_size_items = [item]

            #Custom printings
            if add_custom_personalization:
                team_player_name = 'WILLIAMS'
                team_player_number = '10'
                team_player_id = 'WILLIAMS'
                loader = ProductLoader(item=Product(), response=response)
                loader.add_value(None, item)
                loader.add_value('name', team_player_name)
                loader.add_value('name', team_player_number)
                price = Decimal(item['price']) + Decimal(str(custom_printings['PriceActual']))
                loader.replace_value('price', price)
                if price >= 75:
                    loader.replace_value('shipping_cost', 0)
                identifier = '-'.join((item['identifier'],
                                        str(custom_printings['PrintingID']),
                                        team_player_id))
                loader.replace_value('identifier', identifier)
                custom_item = loader.load_item()
                custom_item['metadata'] = {'player': team_player_name,
                                            'number': team_player_number,
                                            'size': size}
                yield custom_item
                base_size_items.append(custom_item)
            
            #Badges
            printing = printings.get(3)
            if not printing:
                continue
            for base_item in base_size_items:
                loader = ProductLoader(item=Product(), response=response)
                loader.add_value(None, base_item)
                loader.add_value('name', printing['PrintingDescription'])
                price = Decimal(base_item['price']) + Decimal(str(printing['PriceActual']))
                loader.replace_value('price', price)
                identifier = base_item['identifier'] + '-' + str(printing['PrintingID'])
                loader.replace_value('identifier', identifier)
                badge_item = loader.load_item()
                badge_item['metadata'] = base_item['metadata'].copy()
                yield badge_item
