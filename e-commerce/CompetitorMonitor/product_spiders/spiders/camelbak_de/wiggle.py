# -*- coding: utf-8 -*-


"""
Account: CamelBak DE
Name: camelbak_de-wiggle.de
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5013
"""


from scrapy import Spider, Request, FormRequest
from product_spiders.base_spiders.wigglespider import WiggleSpider

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)

from product_spiders.utils import extract_price_eu as extract_price



class CamelBakWiggle(WiggleSpider):
    name = 'camelbak_de-wiggle.de'
    allowed_domains = ['www.wigglesport.de']

    start_urls = ['http://www.wigglesport.de/camelbak/?ps=96']

    _lang_form_lang_id = 'en'
    _lang_form_currencyID = 'EUR'
    _lang_form_countryID = '9'

    do_full_run = True

    def __init__(self, *args, **kwargs):
        super(CamelBakWiggle, self).__init__(*args, **kwargs)

        self.product_ids = {}
        self.matched_identifiers = set()

    def start_requests(self):
        yield Request('http://www.wigglesport.de',
                      dont_filter=True,
                      callback=self.get_currency)

    def get_currency(self, response):
        verification_token = response.xpath('//input[@name="__RequestVerificationToken"]/@value').extract()[0]
        yield FormRequest('http://www.wigglesport.de/internationaloptions/update',
                          formdata={'__RequestVerificationToken': verification_token,
                                    'langId': self._lang_form_lang_id,
                                    'currencyId': self._lang_form_currencyID,
                                    'countryId': self._lang_form_countryID,
                                    'action': 'Update',
                                    'returnUrl': '/',
                                    'cancelUrl': '/'},
                          dont_filter=True,
                          callback=self.init_requests)

    def init_requests(self, response):
        for url in self.start_urls:
            yield Request(url)

    def parse(self, response):
        next_page = response.xpath('//div[@id="pagerMainColumnHeader"]//a[normalize-space(text())=">"]/@href').extract()
        if next_page:
            yield Request(url=next_page[0], callback=self.parse_product_list)

        products = response.xpath('//a[@data-ga-action="Product Title"]/@href').extract()
        if products:
            for product in products:
                yield Request(url=product, callback=self.parse_product)

    def parse_product(self, response):
        for item in self.parse_product_main(response,
            self.product_ids, self.matched_identifiers):
                yield item

    @classmethod
    def parse_product_main(cls, response, self_product_ids, self_matched_identifiers):
        # log.msg(">>>>>>>>>>>>>>> PARSE PRODUCT >>>")

        product_loader = ProductLoader(item=Product(), response=response)
        product_loader.add_value('url', response.url)
        product_loader.add_xpath('name', u'//h1[@id="productTitle"]/text()')
        price = response.xpath(u'//div[contains(@class, "bem-product-price")]/div[contains(@class, "bem-product-price")]//text()').re(r'[\d,.]+')
        if not price:
            price = response.xpath(u'//*[contains(@class, "unit-price")]/text()').re(r'[\d,.]+')
        if price:
            price = price[0]
        else:
            price = '0.0'
        price = extract_price(price)
        if not price:
            discontinued = bool(response.xpath('//div[contains(@class, "discontinuedProduct")]'))
            retry = int(response.meta.get('retry', 0))
            if (not discontinued) and retry < 20:
                meta = response.meta.copy()
                meta['retry'] = retry + 1
                yield Request(response.url, meta=meta, dont_filter=True,
                              callback=lambda r: cls.parse_product_main(r, self_product_ids, self_matched_identifiers))
        if price:
            product_loader.add_value('price', price)
            product_loader.add_xpath('category', u'//ul[@id="breadcrumbs"]/li[2]/div/a/@title')
            product_loader.add_xpath('image_url', u'concat("http:", //img[@itemprop="image"]/@src)')
            product_loader.add_xpath('brand', u'//span[@itemprop="manufacturer"]/text()')
            # product_loader.add_xpath('shipping_cost', '')
            product = product_loader.load_item()

            identifier = response.xpath('//*[@id="quickBuyBox"]/form/input[@name="id"]/@value').extract()
            if identifier:
                # single option product
                prod = Product(product)
                prod['name'] = prod['name'] + ' ' + response.xpath(u'normalize-space(//*[@id="quickBuyBox"]/form/div[@class="option-text"]/text())').extract()[0]
                prod['name'] = prod['name'].strip()
                prod['identifier'] = identifier[0]
                prod['sku'] = identifier[0]
                if prod['identifier'] in self_product_ids:
                    prod['name'] = self_product_ids[prod['identifier']]
                else:
                    self_product_ids[prod['identifier']] = prod['name']
                out_of_stock = response.xpath('//span[contains(@class, "out-of-stock")]')
                if out_of_stock:
                    prod['stock'] = 0

                self_matched_identifiers.add(prod['identifier'])
                yield prod
            else:
                # multiple options product
                option_groups = response.xpath(u'//select[@id="productOptionDropDown2"]/optgroup')
                if option_groups:
                    for option_group in option_groups:
                        label = option_group.xpath('@label').extract()[0]
                        options = option_group.xpath(u'option')
                        for option in options:
                            value = option.xpath(u'./@value').extract()[0]
                            if not value:
                                continue
                            prod = Product(product)
                            opt_name = option.xpath(u'normalize-space(./text())').extract()[0]
                            last_pos = opt_name.find('- Out of stock')
                            if last_pos == -1:
                                last_pos = len(opt_name)
                            prod['name'] = prod['name'] + ' ' + label + ' ' + opt_name[:last_pos].strip()
                            prod['name'] = prod['name'].strip()
                            prod['identifier'] = value
                            prod['sku'] = value
                            stock = option.xpath('./@class').extract()
                            stock = stock[0] if stock else ''
                            if stock.startswith('out'):
                                prod['stock'] = 0
                            if prod['identifier'] in self_product_ids:
                                prod['name'] = self_product_ids[prod['identifier']]
                            else:
                                self_product_ids[prod['identifier']] = prod['name']
                            self_matched_identifiers.add(prod['identifier'])
                            yield prod
                    # root options
                    options = response.xpath(u'//select[@id="productOptionDropDown2"]/option[not(@disabled)]')
                    for option in options:
                        value = option.xpath(u'./@value').extract()[0]
                        if not value:
                            continue
                        prod = Product(product)
                        opt_name = option.xpath(u'normalize-space(./text())').extract()[0]
                        last_pos = opt_name.find('- Out of stock')
                        if last_pos == -1:
                            last_pos = len(opt_name)
                        prod['name'] = prod['name'] + ' ' + label + ' ' + opt_name[:last_pos].strip()
                        prod['name'] = prod['name'].strip()
                        prod['identifier'] = value
                        prod['sku'] = value
                        stock = option.xpath('./@class').extract()
                        stock = stock[0] if stock else ''
                        if stock.startswith('out'):
                            prod['stock'] = 0
                        if prod['identifier'] in self_product_ids:
                            prod['name'] = self_product_ids[prod['identifier']]
                        else:
                            self_product_ids[prod['identifier']] = prod['name']
                        self_matched_identifiers.add(prod['identifier'])
                        yield prod
                else:
                    options = response.xpath(u'//select[@id="productOptionDropDown2"]//option')
                    if options:
                        for option in options:
                            value = option.xpath(u'./@value').extract()[0]
                            if not value:
                                continue
                            prod = Product(product)
                            opt_name = option.xpath(u'normalize-space(./text())').extract()[0]
                            last_pos = opt_name.find('- Out of stock')
                            if last_pos == -1:
                                last_pos = len(opt_name)
                            prod['name'] = prod['name'] + ' ' + opt_name[:last_pos].strip()
                            prod['name'] = prod['name'].strip()
                            prod['identifier'] = value
                            prod['sku'] = value
                            stock = option.xpath('./@class').extract()
                            stock = stock[0] if stock else ''
                            if stock.startswith('out'):
                                prod['stock'] = 0
                            if prod['identifier'] in self_product_ids:
                                prod['name'] = self_product_ids[prod['identifier']]
                            else:
                                self_product_ids[prod['identifier']] = prod['name']
                            self_matched_identifiers.add(prod['identifier'])
                            yield prod
                    else:
                        options = response.xpath('//input[@name="id"]')
                        for option in options:
                            value = option.xpath(u'./@id').extract()
                            if not value:
                                continue
                            prod = Product(product)
                            prod['name'] = prod['name'] + ' ' + ' '.join(option.xpath(u'./@data-colour|./@data-size').extract())
                            prod['name'] = prod['name'].strip()
                            prod['identifier'] = value[0].strip()
                            prod['sku'] = value[0].strip()
                            stock = 'in-stock' in option.xpath('@class').extract()[0]
                            if not stock:
                                prod['stock'] = 0
                            if prod['identifier'] in self_product_ids:
                                prod['name'] = self_product_ids[prod['identifier']]
                            else:
                                self_product_ids[prod['identifier']] = prod['name']
                            self_matched_identifiers.add(prod['identifier'])
                            yield prod
