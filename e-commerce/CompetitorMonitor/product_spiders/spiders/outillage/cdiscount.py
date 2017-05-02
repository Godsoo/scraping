# -*- coding: utf-8 -*-

from product_spiders.spiders.BeautifulSoup import BeautifulSoup
from scrapy import Spider, Request
from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader,
)


class CDiscountSpider(Spider):
    name = 'cdiscount.com'
    allowed_domains = ['cdiscount.com']
    start_urls = [u'http://www.cdiscount.com/bricolage-chauffage/v-117-2.html']

    handle_httpstatus_list = [301, 302]

    RETRY_TIMES = 5

    errors = []

    identifiers = []

    def closing_parse_simple(self, response):
        for item in super(CDiscountSpider, self).closing_parse_simple(response):
            if item['identifier'] not in self.identifiers:
                self.identifiers.append(item['identifier'])
                yield item

    def parse(self, response):
        nonuniq_ids = ['gpmp000000029141', 'gpdcs930l', 'gpdcs942l', 'gpmp000000144794', 'pro3300660800147', 'pro3219510155354']
        # find subcats for Outilage Jardin
        categories = response.xpath('//div[@class="u_1"]/nav/div//ul/li/a/@href').extract()

        categories_text = response.xpath('//div[@class="mvNavLk"]/a/text()').extract()
        categories_text += response.xpath('//div[@class="mvNavSub"]/strong/text()').extract()
        categories_text = ''.join(categories_text).upper()
        has_subcats = False

        if 'BRICO - CHAUFFAGE' in categories_text:
            has_subcats = True
            for url in categories:
                url = response.urljoin(url)
                yield Request(url)

        products_collected = 0
        products = response.xpath('//div[@id="lpContent"]/div/ul/li[div/a]')
        if products:
            for product in products:
                link = product.select('div/a/@href').extract()
                if link:
                    product_loader = ProductLoader(item=Product(), selector=product)
                    product_loader.add_value('url', response.urljoin(link[0]))
                    product_loader.add_xpath('name', 'div//div[@class="prdtBTit"]/text()')
                    category = product.select('//div[@id="bc"]//a[@itemprop="title"]/text()').extract()
                    if category:
                        product_loader.add_value('category', category[0])
                    product_loader.add_xpath('image_url', 'div/a/ul/li/img[@class="prdtBImg"]/@data-src')
                    product_loader.add_xpath('sku', './@data-sku')
                    price = '.'.join(product.select(u'.//div[@class="prdtPrice"]//text()').re(r'\d+')).strip()
                    product_loader.add_value('price', price)
                    if product_loader.get_output_value('name') and product_loader.get_output_value('price'):
                        identifier = product.select('.//input[contains(@name, "ProductPostedForm.ProductId")]/@value').extract()
                        if identifier:
                            identifier = identifier[0].lower()
                            if identifier in nonuniq_ids or identifier in self.identifiers:
                                product_loader.add_xpath('identifier', './@data-sku')
                            else:
                                product_loader.add_value('identifier', identifier)
                            products_collected += 1
                            product_loader.add_value('stock', 1)
                            self.identifiers.append(product_loader.get_output_value('identifier'))
                            yield product_loader.load_item()
                        else:
                            self.log('PRODUCT WITH NO IDENTIFIER => %s' % response.url)
        else:
            self.log('NO PRODUCTS => %s' % response.url)
            if not has_subcats:
                yield self._retry_req(response)
        # pagination
        next_page = response.xpath('//form[@name="PaginationForm"]//a[contains(@class, "pgNext")]/@href').extract()
        if not next_page:
            soup = BeautifulSoup(response.body)
            next_page = soup.find('a', 'pgNext')
            if next_page:
                next_page = [next_page['href']]
        if next_page:
            next_page = response.urljoin(next_page[0])
            yield Request(next_page,
                          meta={'next_page_retry': 1,
                                'dont_redirect': True},
                          dont_filter=True)
        else:
            self.log('NO NEXT PAGE => %s' % response.url)
            if not has_subcats:
                yield self._retry_req(response)

    def _retry_req(self, response):
        meta = response.meta
        retries = meta.get('retries', 0)
        if retries < 5:
            self.log('RETRYING URL => %s (%s)' % (response.url, retries))
            meta['retries'] = retries + 1
            return Request(response.url, meta=meta, dont_filter=True)

    def parse_product(self, response):
        product_loader = ProductLoader(item=Product(), response=response)
        product_loader.add_value('url', response.url)
        product_loader.add_xpath('name', "//h1[@itemprop='name']/text()")
        if not product_loader.get_output_value('name'):
            product_loader.add_xpath('name', "//h2[@itemprop='name']/text()")
        category = response.xpath('//div[@id="bc"]//a[@itemprop="title"]/text()').extract()
        if category:
            product_loader.add_value('category', category[0])
        product_loader.add_xpath('image_url', "//*[@itemprop='image']/@href")
        product_loader.add_xpath('sku', "//input[@id='sku']/@value")
        identifier = response.xpath('//input[@id="TechFormProductId"]/@value').extract()[0].lower()
        product_loader.add_value('identifier', identifier)
        # stock = response.xpath('//link[@itemprop="availability" and contains(@href, "OutOfStock")]')
        # if stock:
        #     product_loader.add_value('stock', 0)
        # else:
        product_loader.add_value('stock', 1)
        price = response.xpath("//*[@itemprop='price']/@content").extract()
        if not price:
            price = response.xpath("//*[@itemprop='lowPrice']/@content").extract()

        if not price:
            return

        price = price[0].replace(",", ".")

        product_loader.add_value('price', price)
        if product_loader.get_output_value('name') and product_loader.get_output_value('price'):
            identifier = product_loader.get_output_value('identifier')
            if identifier and identifier.strip():
                if identifier not in self.identifiers:
                    self.identifiers.append(identifier)
                    yield product_loader.load_item()
                else:
                    self.log('IDENTIFIER ALREADY EXTRACTED: ' + response.url)
            else:
                self.log('NO IDENTIFIER: ' + response.url)
        else:
            self.log('NO NAME OR PRICE: ' + response.url)
