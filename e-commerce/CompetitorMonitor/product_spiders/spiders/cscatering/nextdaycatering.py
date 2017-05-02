
import time
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price

from product_spiders.base_spiders.primary_spider import PrimarySpider

from decimal import Decimal
from copy import deepcopy


class NextDayCateringSpider(PrimarySpider):
    name = 'cscatering-nextdaycatering.co.uk'
    allowed_domains = ['nextdaycatering.co.uk']
    start_urls = ('http://www.nextdaycatering.co.uk',)

    csv_file = 'nextdaycatering_products.csv'

    rotate_agent = True
    max_retry_times = 10
    download_delay = 0.25

    handle_httpstatus_list = [301, 302]

    def start_requests(self):
        yield Request('http://www.nextdaycatering.co.uk', meta={'dont_redirect': True})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//ul[contains(@class, "nav")]//li/a/@href').extract()
        categories += hxs.select('//div[contains(div/text(),"Categories")]//li[contains(@class,"menu-item")]/a/@href').extract()
        categories += hxs.select('//a[@class="sub-entity-name-link"]/@href').extract()
        categories += hxs.select('//div[contains(@class, "category-box")]//a/@href').extract()
        categories += hxs.select('//ul[@class="pagination"]/li[last()]/a/@href').extract()
        for url in categories:
            yield Request(urljoin_rfc(base_url, url),
                          meta={'dont_redirect': True,
                                'dont_merge_cookies': True,
                                'cookiejar': int(time.time())}, callback=self.parse)

        products = hxs.select('//div[contains(@class, "entity-product-name-wrap")]/a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url),
                          meta={'dont_redirect': True,
                                'dont_merge_cookies': True,
                                'cookiejar': int(time.time())},
                          callback=self.parse_product)

        next_page = hxs.select('//a[contains(@class, "nextLink")]/@onclick').re("'(\d+)'")
        if next_page:
            next_page = next_page[0]
            next_url = response.url.split('?')[0] + '?pagenum=' + next_page
            yield Request(next_url, meta={'dont_redirect': True,
                                          'dont_merge_cookies': True,
                                          'cookiejar': int(time.time())})

        if not products and not categories:
            retries = int(response.meta.get('retries', 0))
            if retries < self.max_retry_times:
                retries += 1
                req = Request(response.url, meta={'retries': retries,
                                                  'dont_merge_cookies': True,
                                                  'cookiejar': int(time.time()),
                                                  'dont_redirect': True}, dont_filter=True)
                yield req

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        name = hxs.select('//h1[@class="product-name"]/text()').extract()
        try:
            identifier = hxs.select('//input[contains(@name, "ProductID")]/@value').extract()[0]
        except IndexError:
            retries = int(response.meta.get('retries', 0))
            if retries < self.max_retry_times:
                retries += 1
                req = Request(response.url, meta={'retries': retries,
                                                  'dont_merge_cookies': True,
                                                  'cookiejar': int(time.time()),
                                                  'dont_redirect': True},
                              dont_filter=True,
                              callback=self.parse_product)
                yield req
            return

        sku = hxs.select('//div[contains(@class, "list-item-sku-wrap")]/text()').re('SKU: (.*)')
        sku = sku[0].strip() if sku else ''

        price = hxs.select('//div[@class="price-wrap"]/div[contains(@class, "sale") and contains(@class, "inc-vat")]/span[@itemprop="price"]/text()').extract()
        if not price:
            price = hxs.select('//div[@class="price-wrap"]/div[contains(@class, "regular") and contains(@class, "inc-vat")]/text()').extract()
        price = extract_price(price[0])

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('price', price)
        in_stock = 'IN STOCK' in ''.join(hxs.select('//span[contains(@class, "stock-hint")]/text()').extract()).strip().upper()
        if not in_stock:
            loader.add_value('stock', 0)
        loader.add_value('identifier', identifier)
        loader.add_value('name', name)
        categories = hxs.select('//span[@class="SectionTitleText"]/a/text()').extract()
        loader.add_value('category', categories)

        brand = hxs.select('//ul/li[contains(text(), "Brand:")]/text()').re('Brand: (.*)')
        brand = brand[0].strip() if brand else ''
        loader.add_value('brand', brand)

        loader.add_value('sku', sku)
        loader.add_value('url', response.url)

        image_url = hxs.select('//img[contains(@class, "product-image")]/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))

        if loader.get_output_value('price')>=50:
            loader.add_value('shipping_cost', 0)
        else:
            loader.add_value('shipping_cost', 3.99)
        item = loader.load_item()
        options = hxs.select('//select[@id="variantSelector"]/option')
        if options:
            for option in options:
                option_item = deepcopy(item)
                option_id = option.select('@value').extract()[0]
                option_name = option.select('text()').extract()
                if not option_name or option_item['name'].upper() not in option_name[0].upper():
                    option_name = option_item['name'] +' '+ ''.join(hxs.select('//div[@class="misc-text-promo"]/text()').extract()).strip()
                else:
                    option_name = option_name[0]
                price = hxs.select('//div[@id="variant-info-'+option_id+'"]/div[@class="price-wrap"]/div[contains(@class, "sale") and contains(@class, "inc-vat")]/span[@itemprop="price"]/text()').extract()
                if not price:
                    price = hxs.select('//div[@id="variant-info-'+option_id+'"]/div[@class="price-wrap"]/div[contains(@class, "regular") and contains(@class, "inc-vat")]/text()').extract()
                price = extract_price(price[0])
                price = (price/Decimal('1.2')).quantize(Decimal('1.00'))
                option_item['price'] = price
                option_item['name'] = option_name.strip()
                option_item['identifier'] = option_item['identifier'] + '-' +option_id
                yield option_item
        else:
            yield item

    # Only if Proxy Service enabled
    def proxy_service_check_response(self, response):
        blocked = False
        if hasattr(response, 'meta'):
            redirect_urls = response.meta.get('redirect_urls', [])
            if redirect_urls:
                blocked = bool(filter(lambda u:'blocked.html' in u, redirect_urls))
        return blocked
