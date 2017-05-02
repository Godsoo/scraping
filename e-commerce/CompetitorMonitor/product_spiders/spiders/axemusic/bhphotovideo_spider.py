# -*- coding: utf-8 -*-

import json
from scrapy import Spider, Request
from scrapy.utils.url import canonicalize_url
from product_spiders.items import Product
from axemusic_item import ProductLoader as AxeMusicProductLoader

from product_spiders.base_spiders.bigsitemethodspider import BigSiteMethodSpider


class BhphotoVideoSpider(Spider):
    name = 'axemusic-bhphotovideo.com'
    allowed_domains = ['bhphotovideo.com']

    start_urls = ['http://www.bhphotovideo.com/c/browse/SiteMap/ci/13296/N/4294590034&ipp=100',]

    rotate_agent = True
    download_timeout = 60

    def __init__(self, *args, **kwargs):
        super(BhphotoVideoSpider, self).__init__(*args, **kwargs)

        self.product_pages = set()
        self._today_result_ids = {}

    def start_requests(self):
        for url in self.start_urls:
            yield Request(url, callback=self.parse_full)

    def parse_full(self, response):
        meta = response.meta.copy()
        meta['dont_redirect'] = True
        meta['dont_merge_cookies'] = True

        items_number = response.xpath('//div[contains(@class, "pagination")]//span[contains(@class, "bold")]/text()').re(r'\d+')

        if items_number:
            if items_number[0] > items_number[1]:
                return

        need_retry = False

        brands = response.xpath('//dl[@class="brandsList"]//a/@href').extract()
        for brand in brands:
            yield(Request(brand, callback=self.parse_full))

        cats = response.xpath('//li[@data-selenium="category"]//@href').extract()
        if cats:
            for cat in cats:
                meta['try'] = 0
                yield Request(
                        url=canonicalize_url(cat),
                        callback=self.parse_full,
                        meta=meta,
                        errback=lambda failure, url=canonicalize_url(cat), metadata=meta: self.bsm_retry_download(failure, url, metadata, self.parse_full))

        products = response.xpath(
                '//div[contains(@class, "item") and contains(@class, "clearfix")]')
        if products:
            for product in products:
                try:
                    brand = product.xpath('.//span[@itemprop="brand"]/text()').extract()[0]
                except IndexError:
                    brand = ''
                try:
                    title = product.xpath('.//span[@itemprop="name"]/text()').extract()[0]
                except IndexError:
                    continue
                name = ' '.join((brand, title))

                url = product.xpath('.//a[@itemprop="url"]/@href').extract()[0]

                price = ''.join(product.xpath('.//*[contains(@class, "price")]/text()').extract()).strip()

                identifier = product.xpath('.//input[@name="sku"]/@value').extract()
                if identifier:
                    identifier = identifier[0]
                    id_part = product.xpath('.//input[@name="is"]/@value').extract()
                    if id_part:
                        identifier = identifier + '-' + id_part[0]
                else:
                    self.log('No identifier found for %s on %s' %(name, response.url))
                    continue

                if not price:
                    for data in response.xpath('//div/@data-itemdata').extract():
                        json_data = json.loads(data)
                        if json_data['sku'] in identifier.split('-'):
                            price = json_data['price']
                            break

                sku = product.xpath('.//p[contains(@class, "skus")]//span[@class="sku"]/text()').extract()
                if sku:
                    sku = sku[-1]
                else:
                    sku = ''

                image_url = product.xpath('div/a[@name="image"]/img/@src').extract()
                if not image_url:
                    image_url = product.xpath('div[@class="img-zone zone"]//img/@data-src').extract()
                if not image_url:
                    image_url = product.xpath('div[@class="img-zone zone"]//img/@src').extract()
                if image_url:
                    image_url = response.urljoin(image_url[0])
                else:
                    image_url = ''
                category = response.xpath('//ul[@id="breadcrumbs"]/li/a/text()').extract()[-1].strip()
                if category.lower() == "home":
                    category = response.xpath('//ul[@id="breadcrumbs"]/li[@class="last"]/text()').extract()[-1].strip()

                if identifier:
                    if not price:
                        price = '0.0'

                    loader = AxeMusicProductLoader(item=Product(), selector=product)
                    loader.add_value('url', url)
                    loader.add_value('identifier', identifier)
                    loader.add_value('sku', sku)
                    loader.add_value('image_url', image_url)
                    if brand:
                        loader.add_value('brand', brand)
                    loader.add_value('category', category)
                    loader.add_value('name', name)
                    loader.add_value('price', price)

                    if url not in self.product_pages and loader.get_output_value('price') > 0:
                        item = loader.load_item()
                        if item['identifier'].endswith('-REG'):
                            item['identifier'] = item['identifier'].replace('-REG', '')
                        yield item
                    self.product_pages.add(url)
        elif not cats:
            need_retry = True

        pages = response.xpath('//div[contains(@class, "pagination-zone")]//a/@href').extract()
        for page_url in pages:
            meta['try'] = 0
            yield Request(
                    callback=self.parse_full,
                    url=canonicalize_url(page_url),
                    meta=meta)

        if need_retry:
            retry = response.meta.get('try', 0)
            if retry < 15:
                meta = response.meta.copy()
                meta['try'] = retry + 1
                self.log("Try %d. retrying to download %s" % (meta['try'], response.url))
                yield Request(
                        url=response.url,
                        callback=self.parse_full,
                        dont_filter=True,
                        meta=meta)

    def parse_product(self, response):
        meta = response.meta
        url = response.url
        price = ''
        for line in response.body.split('\n'):
            if "MAIN:No^Refrnce" in line:
                price = line.split('");')[0].split(', "')[-1]

        if not price:
            try:
                price = response.xpath('//span[@itemprop="price"]/text()').extract()[0].replace(',', '')
            except IndexError:
                pass

        identifier = meta.get('identifier')
        if not identifier:
            identifier = response.xpath('//form[@name="addItemToCart"]//input[@name="sku"]/@value').extract()
        if not identifier:
            identifier = response.xpath('//input[@name="useMainItemSku"]/@value').extract()

        id_part = response.xpath('//form/input[@name="is"]/@value').extract()

        if identifier:
            identifier = identifier[0]
            if id_part:
                identifier = identifier + '-' + id_part[0]

        else:
            self.log('Product without identifier: ' + response.url)
            return

        if not price:
            for data in response.xpath('//div/@data-itemdata').extract():
                json_data = json.loads(data)
                if json_data['sku'] in identifier.split('-'):
                    price = json_data['price']
                    break

        image_url = meta.get('image_url')
        if not image_url:
            image_url = response.xpath('//img[@id="mainImage"]/@src').extract()
        brand = meta.get('brand')
        if not brand:
            brand = response.xpath('//div[@id="tMain"]//div[@class="mfrLogo"]//img[1]/@alt').extract()
        category = meta.get('category')
        if not category:
            try:
                category = response.xpath('//ul[@id="breadcrumbs"]/li/a/text()').extract()[-1].strip()
            except IndexError:
                pass
        sku = meta.get('sku')
        if not sku:
            sku = map(lambda s: s.replace(' ', '').lower(),
                      response.xpath('//meta[@itemprop="productID" and contains(@content, "mpn:")]/@content').re(r'mpn:([\w\s\.-]+)'))
        name = meta.get('name')
        if not name:
            name = ''.join(response.xpath('//*[@itemprop="name"]//text()').extract()).strip()

        if identifier:
            loader = AxeMusicProductLoader(item=Product(), response=response)
            loader.add_value('identifier', identifier)
            loader.add_value('image_url', image_url)
            loader.add_value('brand', brand)
            loader.add_value('category', category)
            loader.add_value('url', url)
            loader.add_value('sku', sku)
            loader.add_value('name', name)
            loader.add_value('price', price)

            product = loader.load_item()

            # BSM simple run duplicates fix
            if isinstance(self, BigSiteMethodSpider) and self.simple_run and (product['identifier'] not in self.matched_identifiers):
                self.matched_identifiers.add(product['identifier'])

            if product['price'] > 0:
                if product['identifier'].endswith('-REG'):
                    product['identifier'] = product['identifier'].replace('-REG', '')
                yield product
