"""
Account: Zyro
Name: zyro-bike24.com

IMPORTANT!!

- This spider is blocked, please be careful, the website bans the proxies FOREVER!! and we can't use those there anymore.
- It uses proxies, but the website also take into account the client IP to store session data. So, the location setting didn't work
  well whether need to use different proxies randomly. So this spider use a custom price convertion valid at the moment to convert
  the currency from Germany location to UK location. Please take a look at the `convert_to_pounds` method and the LOCATION_PRICE_CONVERTION
  variable.

TODO:

- Create Bike24 Base Spider, two spiders at the moment crawling this website:

  1. This (zyro-bike24.com)
  2. crc-de-bike24.com (CRC DE account)

"""

from scrapy.http import Request, FormRequest, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter, url_query_cleaner
from product_spiders.base_spiders.bigsitemethodspider import BigSiteMethodSpider
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price
from decimal import Decimal


class Bike24Spider(BigSiteMethodSpider):
    name = 'zyro-bike24.com'
    allowed_domains = ['bike24.com']
    start_urls = ['http://www.bike24.com/']

    exchange_rate = 0
    id_seen = []
    rotate_agent = True

    full_crawl_cron = "21 * *"
    website_id = 1326

    # Price shipping conversion: 1.0084
    LOCATION_PRICE_CONVERTION = '1.0084'

    def _start_requests_full(self):
        yield Request('http://www.xe.com/currencyconverter/convert/?Amount=1&From=EUR&To=GBP',
                      meta={'_parse_simple': False},
                      callback=self.start_bike24_requests)

    def _start_requests_simple(self):
        yield Request('http://www.xe.com/currencyconverter/convert/?Amount=1&From=EUR&To=GBP',
                      meta={'_parse_simple': True},
                      callback=self.start_bike24_requests)

    def closing_parse_simple(self, response):
        for item in super(Bike24Spider, self).closing_parse_simple(response):
            if isinstance(item, Product):
                if 'shipping_cost' in item:
                    del item['shipping_cost']
                # Normalize URL
                item['url'] = url_query_cleaner(item['url'], parameterlist=('content', 'product'), sep=';')
            yield item

    def start_bike24_requests(self, response):
        exchange_rate = response.xpath('//tr[@class="uccRes"]/td[last()]/text()').re('[\d\.]+')[0]

        self.exchange_rate = extract_price(exchange_rate)
        callback = self.start_bike24_requests_simple if response.meta.get('_parse_simple', False) else self.parse
        yield FormRequest('http://www.bike24.com',
                          formdata={'country': '9', 'lang': '2', 'submit': '', '_qf__localeSelectFormQuick': '',
                                    'action': 'locale_select', 'no_ajax_submit': '1', 'promotion': '3'},
                          callback=callback)

    def start_bike24_requests_simple(self, response):
        c = 0
        for res in super(Bike24Spider, self)._start_requests_simple():
            c += 1
            res.meta['cookiejar'] = c
            yield res

    def get_exchange_rate(self, response):
        exchange_rate =  response.xpath('//tr[@class="uccRes"]/td[last()]/text()').re('[\d\.]+')[0]
        self.exchange_rate = extract_price(exchange_rate)
        return None

    def convert_to_pounds(self, price):
        price = extract_price(price)
        price = round(price * Decimal(self.LOCATION_PRICE_CONVERTION) * self.exchange_rate, 2)
        return Decimal(str(price))

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return

        base_url = get_base_url(response)
        locale = response.xpath('//a[@class="text-dropdown-toggle"]/text()[2]').extract()[0].strip()
        self.log(locale)
        for url in response.xpath('//div[contains(@class, "nav-main")]/ul[contains(@class, "nav-main-list-lvl-1")]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_subcategory)

    def parse_subcategory(self, response):
        if not isinstance(response, HtmlResponse):
            return

        base_url = get_base_url(response)
        for link in response.xpath('//ul[@class="nav-main-list-lvl-2"]//a/@href').extract():
            url = urljoin_rfc(base_url, link)
            yield Request(url, callback=self.parse_products_list)

    def parse_products_list(self, response):
        if not isinstance(response, HtmlResponse):
            return

        base_url = get_base_url(response)

        for link in response.xpath('//ul[@class="nav-main-list-lvl-2"]//a/@href').extract():
            url = urljoin_rfc(base_url, link)
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list)

        for link in response.xpath('//div[@class="box-product-list-item-default js-product-link-parent"]/span/a/@href').extract():
            url = urljoin_rfc(base_url, link)
            url = add_or_replace_parameter(url, 'pitems', '50')
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

        for link in response.xpath('//div[@class="col-md-10 box-title-pager hidden-print"]'
                                   '//ul[@class="list-inline list-pager"]//a/@href').extract():
            url = urljoin_rfc(base_url, link)
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list)

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return

        identifier = response.xpath('//form[@id="pdAddToCart"]//input[@name="product"]/@value').extract()
        if not identifier:
            return

        base_url = get_base_url(response)

        loader = ProductLoader(item=Product(), response=response)
        # Normalize URL
        product_url = url_query_cleaner(response.url, parameterlist=('content', 'product'), sep=';')
        loader.add_value('url', product_url)
        loader.add_value('identifier', identifier[0])
        sku = response.xpath('//td[text()="Item Code:"]/following-sibling::td[1]/text()').extract()
        if sku:
            loader.add_value('sku', sku[0])
        loader.add_xpath('name', '//h1[@itemprop="name"]/text()')
        price = response.xpath('//span[@itemprop="price"]/text()').extract()
        if price:
            price = extract_price(price[0].strip().replace('.','').replace(',','.'))
            loader.add_value('price', self.convert_to_pounds(str(price)))
        else:
            loader.add_value('price', '0.0')

        image_url = response.xpath('//img[@itemprop="image"]/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        brand = response.xpath('//td[text()="Manufacturer:"]/following-sibling::td[1]/text()').extract()
        if brand:
            loader.add_value('brand', brand[0])

        category = response.xpath('//main//span[@class="text-title"]/text()').extract()
        if category:
            loader.add_value('category', category[0].split(':')[0].strip())

        availability = response.xpath('//div[@class="pd-availability"]/span[contains(text(),"Delivery")]/text()').extract()
        if availability and 'unknown' in availability[0].lower():
            loader.add_value('stock', 0)

        product = loader.load_item()
        options = response.xpath('//form[@id="pdAddToCart"]//select')
        if not options:
            if not (getattr(self, 'simple_run', False) and (hasattr(self, 'matched_identifiers')) \
               and (product['identifier'] not in self.matched_identifiers)):

                if not product['identifier'] in self.id_seen:
                    self.id_seen.append(product['identifier'])
                    yield product

            return

        for sel in options:
            opt = ''
            select_name = sel.xpath('@name').extract()
            if select_name:
                opt = select_name[0].replace('opt_','')
            for option in sel.xpath('option[@value!="-2"]'):
                item = Product(product)
                opt_id = option.xpath('@value').extract()
                if opt_id:
                    item['identifier'] += '-' + opt + '-' + opt_id[0]
                    item['stock'] = 1
                    if option.xpath('@data-av')=='100':
                        item['stock'] = 0
                    opt_name = option.xpath('text()').extract()
                    if opt_name:
                        item['name'] += ' - ' + opt_name[0]
                    opt_surcharge = option.xpath('@data-surcharge').extract()
                    if opt_surcharge:
                        item['price'] += extract_price(opt_surcharge[0])

                    if getattr(self, 'simple_run', False) and (hasattr(self, 'matched_identifiers')) \
                       and (item['identifier'] not in self.matched_identifiers):
                        continue

                    if not item['identifier'] in self.id_seen:
                        self.id_seen.append(item['identifier'])
                        yield item
