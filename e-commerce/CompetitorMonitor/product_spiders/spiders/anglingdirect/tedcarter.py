import os
import csv

from scrapy import Spider, Request, FormRequest
from scrapy.utils.url import add_or_replace_parameter

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)
from product_spiders.config import DATA_DIR


class TedCarterSpider(Spider):
    name = 'tedcarter.co.uk'
    allowed_domains = ['tedcarter.co.uk']
    start_urls = ('http://www.tedcarter.co.uk/',)

    _products = {}

    def __init__(self, *args, **kwargs):
        super(TedCarterSpider, self).__init__(*args, **kwargs)
        self.errors = []

    def start_requests(self):
        yield FormRequest('http://www.tedcarter.co.uk/',
                          formdata={'country': 'GB', 'countrySelect': 'Change Country'},
                          callback=self.parse_default)

    def parse_default(self, response):
        # scrape previous crawl results
        if hasattr(self, 'prev_crawl_id'):
            prev_crawl_res_file = os.path.join(DATA_DIR, '%s_products.csv' % self.prev_crawl_id)
            with open(prev_crawl_res_file) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    yield Request(row['url'], self.parse_product, meta={'brand': row['brand']})

        # Scrape start urls
        for url in self.start_urls:
            yield Request(url, dont_filter=True)

        # Scrape search all
        yield Request('http://www.tedcarter.co.uk/browse?string=', callback=self.parse_list)

    def parse(self, response):
        # categories
        categories = response.xpath('//nav//a/@href').extract()
        for url in categories:
            url = response.urljoin(url)
            yield Request(url, self.parse_list)

    def parse_list(self, response):
        subcats = response.xpath('//div[@class="subcat"]//a/@href').extract()
        for url in subcats:
            yield Request(response.urljoin(url))

        # pages
        last_page = response.xpath(u'//div[@class="pages"]/span/a/text()').extract()
        url_parts = response.url.split('&')
        if last_page:  # make requests only from page 1
            last_page = int(last_page[-1])
            for i in xrange(2, last_page + 1):
                url = add_or_replace_parameter(url_parts[0], 'perPage', '20')
                url = add_or_replace_parameter(url, 'currentPage', str(i))
                yield Request(url, callback=self.parse_list)

        pages = response.xpath('//div[@class="pagination"]//a/@href').extract()
        for url in pages:
            yield Request(response.urljoin(url),
                          callback=self.parse_list)

        # products
        products = response.xpath('//div[contains(@class, "products-wrap")]//a[@href]')

        for product in products:
            yield Request(response.urljoin(product.select('@href').extract()[0]), callback=self.parse_product, meta={'brand':product.select('./div[@class="brand"]/text()').extract()[0].strip()})

        if not products:
            meta = response.meta.copy()
            meta['retry'] = meta.get('retry', 0) + 1
            if meta['retry'] < 10:
                yield Request(response.url,
                              callback=self.parse_list,
                              meta=meta,
                              dont_filter=True)
            else:
                self.log('WARNING: No products in %s' % response.url)


    def parse_product(self, response):
        image_url = response.xpath('//div[@class="main-image"]/img/@src').extract()
        if image_url:
            image_url = response.urljoin(image_url[-1])
        category = response.xpath(u'//ol[@id="breadcrumbs"]/li/a/span[@itemprop="title"]/text()').extract()
        category = category[0] if category else ''
        brand = response.meta['brand']

        multiple_prices = response.xpath('//label[text()="Options"]/../select/option')
        if not multiple_prices:
            identifier = response.xpath('//input[@name="sku"]/@value').extract()
            if not identifier:
                return
            else:
                identifier = identifier[0]
            price = response.xpath('//div[@class="price"]/span[@class="text"]/text()').re(r'[\d\.,]+')
            if not price:
                price = response.xpath('//div[@class="price"]/span[@class="text"]//text()').re(r'[\d\.,]+')
            product_loader = ProductLoader(item=Product(), response=response)
            product_loader.add_xpath('name', '//div[@class="name"]/h1/text()')
            if image_url:
                product_loader.add_value('image_url', image_url)
            product_loader.add_value('brand', brand)
            product_loader.add_value('category', category)
            product_loader.add_value('url', response.url)
            product_loader.add_value('identifier', identifier)
            product_loader.add_value('price', price)
            item = product_loader.load_item()

            # Try to solve "same product" issue but different name, price and url
            # Will be collected the lower price
            if item['identifier'] in self._products:
                item['name'] = self._products[item['identifier']]['name']
                item['url'] = self._products[item['identifier']]['url']
            else:
                self._products[item['identifier']] = {
                    'name': item['name'],
                    'url': item['url'],
                }

            yield item
        else:
            for name_and_price in multiple_prices:
                product_loader = ProductLoader(item=Product(), selector=name_and_price)
                name = response.xpath('//div[@class="name"]/h1/text()').extract()[0]
                name += ' ' + name_and_price.select('text()').extract()[0].strip()
                try:
                    opt_id = name_and_price.select('@data-sku').extract()[0]
                except:
                    continue
                product_loader.add_value('name', name)
                if image_url:
                    product_loader.add_value('image_url', image_url)
                product_loader.add_value('brand', brand)
                product_loader.add_value('category', category)
                product_loader.add_value('url', response.url)
                product_loader.add_value('identifier', opt_id)
                price = name_and_price.select('@data-price').extract()
                if not price:
                    price = name_and_price.select(u'./td[position()=2]/p[@class="now-table"]/text()').extract()
                if not price:
                    price = name_and_price.select(u'.//*[@itemprop="price"]/text()').extract()
                product_loader.add_value('price', price)

                if name_and_price.select('@data-stock').extract() == ['0']:
                    continue
                item = product_loader.load_item()

                # Try to solve "same product" issue but different name, price and url
                # Will be collected the lower price
                if item['identifier'] in self._products:
                    item['name'] = self._products[item['identifier']]['name']
                    item['url'] = self._products[item['identifier']]['url']
                else:
                    self._products[item['identifier']] = {
                        'name': item['name'],
                        'url': item['url'],
                    }

                yield item
