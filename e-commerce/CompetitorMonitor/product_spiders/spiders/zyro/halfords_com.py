"""
Account: Zyro
Name: zyro-halfords.com
"""


import json
import re
from scrapy import Spider, Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price


class HalfordsComSpider(Spider):
    name = 'zyro-halfords.com'
    allowed_domains = ['halfords.com', 'competitormonitor.com']
    start_urls = ('http://www.halfords.com/cycling',)

    image = 'http://i1.adis.ws/i/washford/%s?$pd_main$'

    def parse(self, response):
        for url in response.xpath('//ul[contains(@class, "sideNav-ul")]/li/a/@href').extract():
            yield Request(response.urljoin(url), callback=self.parse_category_or_product_list)
        for url in response.xpath('//*[@class="pillar-mainSideNav"]/h2/a/@href').extract():
            yield Request(response.urljoin(url), callback=self.parse_category_or_product_list)

    def parse_category_or_product_list(self, response):
        try:
            categories_urls = response.xpath('//span[@class="categoryTitle"]/a/@href').extract()
        except:
            retry = response.meta.get('retry', 0)
            if retry < 10:
                retry = retry + 1
                meta = response.meta.copy()
                meta['retry'] = retry
                self.log('>>> ERROR: Retrying No. %s => %s' % (str(retry), response.url))
                yield Request(response.url,
                              meta=meta,
                              dont_filter=True,
                              callback=self.parse_category_or_product_list)
                return
            else:
                categories_urls = []

        if categories_urls:
            for url in categories_urls:
                yield Request(response.urljoin(url), callback=self.parse_category_or_product_list)
        else:

            # pagination
            next_page = response.xpath('//a[@class="pageLink next"]/@href').extract()
            if next_page:
                yield Request(response.urljoin(next_page[0]), callback=self.parse_category_or_product_list)

            for product_url in response.xpath('//*[@id="product-listing"]//a[@class="productModuleTitleLink"]/@href').extract():
                yield Request(response.urljoin(product_url), self.parse_product)

    def parse_product(self, response):
        try:
            category = response.xpath('//nav[@id="breadcrumb"]//ul/li[@class="penultimateStep"]/a/text()').extract()[0].strip()
        except IndexError:
            category = ''
        image_url = response.xpath('//div[@id="productImage"]//img[@id="fullImage"]/@src|//div[@id="productMainImage"]//img/@src').extract()
        if not image_url:
            image_url = response.xpath('//img[@id="tempImage"]/@src').extract()
        brand = response.xpath('//div[@class="hproduct"]/span[@class="brand"]/text()').extract()
        rrp = response.xpath('//span[@class="rrpValue"]/text()').extract()
        rrp = str(extract_price(rrp[0])) if rrp else ''

        options = re.search('multiVariantArray:(.*),', response.body)
        if options:
            options = json.loads(options.group(1).strip())
            for option in options:
                productId = response.xpath('//form[@id="OrderItemAddForm"]/input[@name="productId"]/@value').extract()[0]
                storeId = response.xpath('//form[@id="OrderItemAddForm"]/input[@name="storeId"]/@value').extract()[0]
                categoryId = response.xpath('//form[@id="OrderItemAddForm"]/input[@name="cmCategoryId"]/@value').extract()[0]
                langId = response.xpath('//form[@id="OrderItemAddForm"]/input[@name="langId"]/@value').extract()[0]
                catalogId = response.xpath('//form[@id="OrderItemAddForm"]/input[@name="catalogId"]/@value').extract()[0]
                catEntryId = option['itemId']
                url = "http://www.halfords.com/webapp/wcs/stores/servlet/GetProductItemDetails?action=getProductItemDetails&" \
                      "msg=%7B%22productId%22%3A%22{}%22%2C%22categoryId%22%3A%22{}" \
                      "%22%2C%22catEntryId%22%3A{}%2C%22catalogId%22%3A%22{}%22%7D&storeId={}&langId={}".format(productId,
                                                                                                                categoryId,
                                                                                                                catEntryId,
                                                                                                                catalogId,
                                                                                                                storeId,
                                                                                                                langId)
                meta = response.meta
                meta['url'] = response.url
                meta['category'] = category
                meta['image_url'] = image_url
                meta['brand'] = brand
                meta['rrp'] = rrp
                yield Request(url, meta=meta, callback=self.parse_product_data)

        else:
            identifier = response.xpath('//input[@name="productId"]/@value').extract()
            if not identifier:
                return

            product_loader = ProductLoader(item=Product(), response=response)
            sku = response.xpath('//input[@name="catCode"]/@value').extract() or response.xpath('//div[@class="itemscode"]/span/text()').extract() or re.findall('setTargeting\("productid","([0-9]+)"\)', response.body) or re.findall(r'productId: "(\d+)"', response.body)
            product_loader.add_value('identifier', identifier)
            if sku:
                sku = sku.pop()
                product_loader.add_value('sku', sku)
                if not image_url and sku:
                    image_url = self.image % sku
            product_loader.add_xpath('name', '//h1[@class="productDisplayTitle"]/text()')
            price = response.xpath('//div[@id="priceAndLogo" or @id="priceAndRating"]/h2/text()').re(r'[\d,.]+')
            if not price:
                self.log('WARNING: No price can be found, ignoring this product.')
            else:
                price = extract_price(price[0])
                if price:
                    product_loader.add_value('price', price)
                    product_loader.add_value('url', response.url)
                    product_loader.add_value('category', category)
                    product_loader.add_value('image_url', image_url)
                    product_loader.add_value('brand', brand)
                    yield product_loader.load_item()

    def parse_product_data(self, response):
        s = response.body
        try:
            content = unicode(s, 'utf-8', errors='replace')
        except (LookupError, TypeError):
            content = unicode(s, errors='replace')
        try:
            data = json.loads(content)
        except ValueError:
            meta = response.meta
            retry = meta.get('retry', 1)
            retry += 1
            if retry < 10:
                meta['retry'] = retry
                self.log('WARNING - Retry #{} {}'.format(retry, response.meta.get('url')))
                yield Request(response.url,
                              meta=meta,
                              callback=self.parse_product_data,
                              dont_filter=True)
            else:
                self.log('ERROR - Maximum retry count reached! {} {}'.format(response.meta.get('url'), response.body))
                yield []
        else:
            item = data.get('productItemDetails')
            if item:
                product_loader = ProductLoader(item=Product(), response=response)
                product_loader.add_value('name', item.get('name'))
                price = extract_price(item.get('nowPriceRaw'))
                if price:
                    product_loader.add_value('price', price)
                    product_loader.add_value('category', response.meta.get('category'))
                    product_loader.add_value('url', response.meta.get('url'))
                    product_loader.add_value('image_url', self.image %item.get('itemCode'))
                    product_loader.add_value('brand', response.meta.get('brand'))
                    product_loader.add_value('sku', item.get('itemCode'))
                    product_loader.add_value('identifier', item.get('itemId'))
                    yield product_loader.load_item()
