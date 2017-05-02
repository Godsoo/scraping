from copy import deepcopy

from scrapy.spider import BaseSpider
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter

from product_spiders.items import Product, ProductLoader

from product_spiders.utils import extract_price

class climaxtackle_spider(BaseSpider):
    name = 'climaxtackle.com'
    allowed_domains = ['climaxtackle.com', 'www.climaxtackle.com']
    start_urls = ('http://www.climaxtackle.com/by-manufacturer.html',)

    def parse(self, response):
        search_url = 'http://www.climaxtackle.com/catalogsearch/result/?cat=0'
        brands = set(response.xpath('//a[contains(@href, "by-manufacturer/")]/text()').extract())
        for brand in brands:
            url = add_or_replace_parameter(search_url, 'q', brand.encode('utf-8'))
            yield Request(url, callback=self.parse_brand,
                          errback=lambda failure, url=url, retries=0, callback=self.parse_brand, item=None: self.retry(failure, url, retries, callback, item))

    def parse_brand(self, response):
        if not isinstance(response, HtmlResponse):
            return

        # pages
        pages_urls = response.xpath('//div[@class="pages"]//a/@href').extract()
        for page in pages_urls:
            yield Request(page, callback=self.parse_brand,
                          errback=lambda failure, url=response.urljoin(page), retries=0,
                                         callback=self.parse_brand, item=None: self.retry(failure, url, retries, callback, item))

        # products
        for p in self.parse_list(response):
            yield p

    def parse_list(self, response):
        products = response.xpath('//div[@class="item-inner"]')
        for p in products:
            try:
                name = p.xpath('.//h2[@class="product-name"]/a/text()').extract()[0].strip()
            except:
                continue
            if name:
                item = {}
                item['name'] = name
                item['url'] = p.xpath('.//h2[@class="product-name"]/a/@href').extract()[0]
                try:
                    item['price'] = extract_price(p.xpath('.//*[@class="price-box"]//text()').re(r'[\d\.,]+')[0])
                except:
                    self.log('WARNING: no price in %s' % response.url)
                    continue
                image_url = p.xpath('.//a[@class="product-image"]/img/@src').extract()
                if image_url:
                    item['image_url'] = urljoin_rfc(get_base_url(response), image_url[0])

                yield Request(item['url'],
                              callback=self.parse_product,
                              meta={'product': item},
                              errback=lambda failure, url=response.urljoin(item['url']), retries=0, callback=self.parse_product, item=item: self.retry(failure, url, retries, callback, item))

    def retry(self, failure, url, retries, callback, item):
        self.log('Error found while loading %s' % url)
        if retries < 10:
            self.log('Retrying loading %s' % url)
            yield Request(url, dont_filter=True, callback=callback,
                          meta={'recache': True, 'product': item},
                          errback=lambda failure, url=url, retries=retries + 1, callback=callback, item=item: self.retry(failure, url, retries, callback, item))
        else:
            self.log('Gave up retrying %s' % url)

    def parse_product(self, response):
        product = response.meta.get('product')

        loader = ProductLoader(item=Product(product), response=response)

        category = response.xpath('//div[@class="breadcrumbs"]//li/a/text()').extract()
        category = category[-1] if category else ''

        loader = ProductLoader(item=Product(product), response=response)
        loader.add_value('category', category)

        product_brand = response.xpath('//tr[th/text()="Manufacturer"]/td/text()').extract()

        loader.add_value('brand', product_brand)

        identifier = response.xpath('//input[@name="product" and @value!=""]/@value').extract()[0]
        loader.add_value('identifier', identifier)
        sku = response.xpath('//tr[th[contains(text(), "Product")]]/td/text()').extract()
        if not sku:
            sku = response.xpath('//tr[th[contains(text(), "Model")]]/td/text()').extract()
        sku = sku[0].strip() if sku else ''
        loader.add_value('sku', sku)

        new_item = loader.load_item()

        table_options = response.xpath('//table[@id="super-product-table"]/tbody/tr')
        option_selector = response.xpath('//div[@class="product-options"]//select')
        if table_options:
            for option in table_options:
                option_item = deepcopy(new_item)
                option_item['name'] = option.xpath('td[1]/text()').extract()[0]
                price = option.xpath('td//span[@class="price"]/text()').extract()
                price = extract_price(price[0]) if price else 0
                option_item['price'] = price
                identifier = option.xpath('td//input/@name').re('\[(.*)\]')
                if not identifier:
                    identifier = option.xpath('td//span/@id').re('product-price-(.*)')
                    option_item['stock'] = 0

                option_item['identifier'] += '-' + identifier[0]
                yield option_item
        elif option_selector:
            for option in option_selector[0].xpath('option[@value!=""]'):
                option_item = deepcopy(new_item)
                option_item['identifier'] += '-' + option.xpath('@value').extract()[0]
                option_item['name'] += ' ' + option.xpath('text()').extract()[0]
                option_item['price'] += extract_price(option.xpath('@price').extract()[0])
                yield option_item
        else:
            yield new_item
