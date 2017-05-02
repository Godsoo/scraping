from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest

from product_spiders.base_spiders.bigsitemethodspider import BigSiteMethodSpider
from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)
from product_spiders.utils import extract_price

from scrapy.item import Item, Field

class CRCMeta(Item):
    rrp = Field()
    ean = Field()
    manufacturer_number = Field()


class WiggleSpider(BigSiteMethodSpider):
    name = 'wiggle.co.uk'
    allowed_domains = ['wiggle.co.uk']
    start_urls = ('http://www.wiggle.co.uk',)
    new_system = True
    download_delay = 0
    website_id = 484948

    # do_full_run = False
    full_crawl_day = 5

    product_ids = {}

    _lang_form_lang_id = 'en'
    _lang_form_currencyID = 'GBP'
    _lang_form_countryID = '1'

    '''
    __RequestVerificationToken:k5rd75EgVetmpQeXwB2wRGhmRlyA6e9eMjYqxB64uIc+6trvOq0hwt/i+4vFMIOw0z9AdzYkb0zi1duRIDax1tOguEy1bshshxETVFFpCUmbUGN/l23GRlY7pCG6xqgbomEnKQ==
    langId:en
    currencyId:GBP
    countryId:1
    action:Update
    returnUrl:/poc-trabec-race-mips-helmet/
    cancelUrl:/poc-trabec-race-mips-helmet/
    '''

    def _start_requests_full(self):
        r = Request('http://www.wiggle.co.uk', dont_filter=True,
                    meta={'callback': self._start_requests_full2}, callback=self.get_currency)
        yield r

    def _start_requests_full2(self, response):
        for r in super(WiggleSpider, self)._start_requests_full():
            yield r

    def _start_requests_simple(self):
        r = Request('http://www.wiggle.co.uk', dont_filter=True,
                    meta={'callback': self._start_requests_simple2}, callback=self.get_currency)
        yield r

    def _start_requests_simple2(self, response):
        for r in super(WiggleSpider, self)._start_requests_simple():
            yield r
    '''
    def get_currency_request(self, callback):
        return FormRequest(
            url='http://www.wiggle.co.uk/internationaloptions/update',
            formdata={
                'langId': self._lang_form_lang_id,
                'currencyId': self._lang_form_currencyID,
                'countryId': self._lang_form_countryID,
                'action': 'Update'},
            callback=callback)
    '''

    def get_currency(self, response):
        verification_token = response.xpath('//input[@name="__RequestVerificationToken"]/@value').extract()[0]
        yield FormRequest('http://www.wiggle.co.uk/internationaloptions/update',
                          formdata={'__RequestVerificationToken': verification_token,
                                    'langId': self._lang_form_lang_id,
                                    'currencyId': self._lang_form_currencyID,
                                    'countryId': self._lang_form_countryID,
                                    'action': 'Update',
                                    'returnUrl': '/',
                                    'cancelUrl': '/'},
                          dont_filter=True,
                          callback=response.meta['callback'])

    def parse_full(self, response):
        # log.msg(">>>>>>>>>>>>>>> PARSE FULL >>>")
        cats = response.xpath("//ul[@class='active-cat']/li/a/@href|//ul[@class='areasMenu hoverintent']/li/a/@href").extract()
        cats = [u'http://www.wiggle.co.uk/bikes/', u'http://www.wiggle.co.uk/components/',
                u'http://www.wiggle.co.uk/clothing/', u'http://www.wiggle.co.uk/shoes/',
                u'http://www.wiggle.co.uk/nutrition/', u'http://www.wiggle.co.uk/accessories/',
                u'http://www.wiggle.co.uk/events/']
        for cat in cats:
            yield Request(
                url=cat,
                callback=self.parse_product_list)

    def parse_product_list(self, response):
        # log.msg(">>>>>>>>>>>>>>> PARSE PRODUCT LIST >>>")
        next_page = response.xpath('//div[@id="pagerMainColumnHeader"]//a[normalize-space(text())=">"]/@href').extract()
        if next_page:
            # log.msg(">>>>>>>>>>>>>>> TURN TO NEXT PAGE >>>")
            yield Request(url=next_page[0], callback=self.parse_product_list)

        products = response.xpath('//a[@data-ga-action="Product Title"]/@href').extract()
        # log.msg(">>>>>>>>>>>>>>> FOUND %s ITEMS >>>" % len(products))
        if products:
            for product in products:
                yield Request(url=product, callback=self.parse_product)


    def parse_product(self, response):
        for item in self.parse_product_main(response, self.product_ids, self.matched_identifiers):
            yield item

    @classmethod
    def parse_product_main(cls, response, self_product_ids, self_matched_identifiers):
        # log.msg(">>>>>>>>>>>>>>> PARSE PRODUCT >>>")
        hxs = HtmlXPathSelector(response)

        product_loader = ProductLoader(item=Product(), selector=hxs)
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

            metadata = CRCMeta()
            metadata['rrp'] = cls.extract_rrp(response)
            product['metadata'] = metadata

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
                if not out_of_stock:
                    out_of_stock = response.xpath('//div[@id="productAvailabilityMessage" and contains(@class, "out-of-stock")]')
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

    def closing_parse_simple(self, response):
        for item in super(WiggleSpider, self).closing_parse_simple(response):
            if isinstance(item, Product):
                if item['identifier'] in self.product_ids:
                    continue
            yield item

    @classmethod
    def extract_rrp(cls, response):
        rrp = response.xpath('//span[contains(text(), "List Price")]/text()').extract()
        rrp = extract_price(rrp[0]) if rrp else ''
        return str(rrp)
