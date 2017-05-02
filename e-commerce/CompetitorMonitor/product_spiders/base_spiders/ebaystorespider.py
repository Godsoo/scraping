"""
Spider to use with spiders built for eBay stores websites
"""


import re
import demjson
from scrapy import Spider, Request, Selector
from product_spiders.utils import extract_price
from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)

class eBayStoreSpider(Spider):
    name = 'stores.ebay.com'
    allowed_domains = [
        'stores.ebay.com',
        'stores.ebay.co.uk',
        'ebay.com',
        'ebay.co.uk']

    id_as_sku = False
    just_last_category = False

    def __init__(self, *args, **kwargs):
        super(eBayStoreSpider, self).__init__(*args, **kwargs)
        self.extract_price = extract_price
        self._extract_stock_amount = True

    def parse(self, response):
        next_page = response.xpath('//table[@class="pager"]//td[@class="next"]/a[1]/@href').extract()
        if not next_page:
            next_page = response.xpath('//a[contains(@class, "nextBtn")]/@href').extract()

        if next_page:
            yield Request(response.urljoin(next_page[0]))

        item_urls = set(response.xpath('//a[@itemprop="url" or @itemprop="name" or @class="vi-url"]/@href').extract())

        for item_url in item_urls:
            yield Request(item_url, callback=self.parse_product)

    def parse_product(self, response):
        if response.xpath('//div[@id="ResultSetItems"]'):
            for x in self.parse(response):
                yield x
            return


        first_name = ' '.join(response.xpath('//*[@id="itemTitle"]/text()')
                              .extract()).strip()
        if not first_name:
            return

        identifier = response.url.split('?')[0].split('/')[-1]

        try:
            category = response.xpath('//ul[@itemtype="http://schema.org/Breadcrumblist"]')[0]\
                               .xpath('.//span[@itemprop="name"]/text()').extract()[1:]
        except:
            category = []
        if category and self.just_last_category:
            category = category.pop()

        seller_id = ''.join(response.xpath('.//*[contains(@class, "si-content")]'
                                        '//a/*[@class="mbg-nw"]/text()').extract())

        brand = filter(lambda s: s.strip() != '',
            response.xpath('//*[@class="attrLabels" and contains(text(), "Brand")]'
                           '/following-sibling::*[1]//text()').extract())
        if not brand:
            brand = filter(lambda s: s.strip() != '',
                response.xpath('//*[@class="attrLabels" and contains(text(), "Brand")]'
                               '/following-sibling::*[1]/h2/text()').extract())
        if not brand:
            brand = filter(lambda s: s.strip() != '',
                response.xpath('//*[@class="attrLabels" and contains(text(), "Brand")]'
                               '/following-sibling::*[1]/h3/text()').extract())
        if not brand:
            brand = filter(lambda s: s.strip() != '',
                response.xpath('//*[@class="attrLabels" and contains(text(), "Marke")]'
                               '/following-sibling::*[1]//text()').extract())
        if not brand:
            brand = filter(lambda s: s.strip() != '',
                response.xpath('//*[@class="attrLabels" and contains(text(), "Hersteller")]'
                               '/following-sibling::*[1]//text()').extract())
        if not brand:
            brand = filter(lambda s: s.strip() != '',
                response.xpath('//*[@class="attrLabels" and contains(text(), "Marque")]'
                               '/following-sibling::*[1]//text()').extract())

        product_loader = ProductLoader(item=Product(), response=response)
        product_loader.add_value('name', first_name)
        product_loader.add_value('identifier', identifier)
        if self.id_as_sku:
            product_loader.add_value('sku', identifier)
        product_loader.add_value('category', category)
        product_loader.add_value('dealer', 'eBay - ' + seller_id)
        product_loader.add_value('brand', brand)
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
        product_loader.add_value('price', self.extract_price(price))

        # shipping cost
        try:
            shipping_cost = response.xpath('//*[@id="shippingSection"]//td/div/text()').extract()[0]
            if shipping_cost:
                if 'free' in shipping_cost.lower():
                    product_loader.add_value('shipping_cost', 0)
                else:
                    product_loader.add_value('shipping_cost', self.extract_price(shipping_cost))
        except:
            pass

        # stock amount
        if self._extract_stock_amount:
            stock = ''
            try:
                in_stock = ''.join(response.xpath('//*[@id="qtySubTxt"]//text()').extract())
                stock = ''
                for match in re.finditer(r"([\d]+)", in_stock):
                    if len(match.group()) > len(stock):
                        stock = match.group()
                if 'More than' in in_stock:
                    stock = 11
            except:
                pass
            if stock:
                product_loader.add_value('stock', stock)

        product_ = product_loader.load_item()

        options_variations = []

        sel = Selector(text=response.body.replace('&quot;', ''))
        try:
            json_var_map = unicode(sel.xpath('//*/text()')
                                   .re(r'("menuItemMap":{.*}.*),'
                                       '"unavailableVariationIds"')[0])
        except:
            pass
        else:
            try:
                variations = demjson.decode('{' + re.sub(r',"unavailableVariationIds".*', '', json_var_map) + '}')

                menu_map = variations['menuItemMap']

                for key, variation in variations['itemVariationsMap'].items():
                    if variation['traitValuesMap']:
                        new_variation = {}
                        for option, value in variation['traitValuesMap'].items():
                            new_variation[option] = menu_map[str(value)]['displayName']
                        options_variations.append({'price': variation['price'],
                                                   'values': new_variation,
                                                   'stock': variation['quantityAvailable'],
                                                   'identifier': '%s:%s' % (identifier, key)})
            except:
                retry_no = int(response.meta.get('retry_no', 0)) + 1
                if retry_no <= 10:
                    self.log('Retrying No. %s => %s' % (retry_no, response.url))
                    req = response.request.copy()
                    req.meta['retry_no'] = retry_no
                    req.dont_filter = True
                    yield req
                else:
                    self.log('Gave up retrying => %s' % response.url)
                return

        if options_variations:
            for model in options_variations:
                model_name = first_name + ' ' + \
                    ' '.join(opt_name.strip().lower()
                             for o, opt_name in model['values'].items())
                new_product = Product(product_)
                new_product['name'] = model_name
                new_product['identifier'] = model['identifier']
                new_product['price'] = self.extract_price(model['price'])
                new_product['stock'] = model['stock']

                yield new_product
        else:
            yield product_
