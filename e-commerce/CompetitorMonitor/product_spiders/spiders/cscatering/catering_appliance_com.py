from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price
from product_spiders.base_spiders.primary_spider import PrimarySpider
# import copy
# import itertools


class CateringApplianceComSpider(PrimarySpider):
    name = 'catering-appliance.com'
    allowed_domains = ['catering-appliance.com']
    start_urls = ('http://www.catering-appliance.com/categories/',)

    csv_file = 'cateringappliancecom_products.csv'

    ignore_brands = ['CRAVEN']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # parse categories
        categories = hxs.select('//div[contains(@class, "catitem")]/a/@href').extract()
        categories += hxs.select('//div[@class="pgitem"]/a/@href').extract()
        for url in categories:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse)
        # parse products
        for url in hxs.select('//div[@class="title"]/h2/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        name = hxs.select('//h1//span[@itemprop="name"]/text()').extract()[0]

        brand = hxs.select('//h1//span[@itemprop="brand"]/text()').extract()
        brand = brand[0].strip() if brand else ''
        if brand.upper() in self.ignore_brands:
            return

        image_url = hxs.select('//div[@class="productimg_container"]/a/img/@src').extract()
        identifier = hxs.select('//*[@id="basketform"]//input[@name="product_id"]/@value').extract()
        if not identifier:
            identifier = hxs.select('//span[@itemprop="sku"]/text()').extract()
        identifier = identifier[0]

        price = response.css('.product_price #exvatprice ::text').extract()
        if not price:
            price = response.xpath('//span[@itemprop="price"]/text()').extract()
            if not price:
                self.log('Warning: no price found! %s' %response.url)
                return
        price = extract_price(price[0])

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('price', price)
        stock = hxs.select('//span[@class="stockstatus"]/span[@class="stock" and contains(text(), "In Stock")]')
        if not stock:
            loader.add_value('stock', 0)
        loader.add_value('identifier', identifier)
        loader.add_value('name', name)
        categories = hxs.select('//div[@itemprop="breadcrumb"]//a/text()').extract()
        loader.add_value('category', categories)
        loader.add_value('brand', brand)
        loader.add_xpath('sku', '//td[@itemprop="mpn"]/text()')
        loader.add_value('url', response.url)
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        shipping = hxs.select('//div[@class="delivery_text"]/strong/text()').extract()
        if shipping:
            if shipping[0] == 'FREE':
                loader.add_value('shipping_cost', 0)
            else:
                loader.add_value('shipping_cost', extract_price(shipping[0]))
        yield loader.load_item()
        # client do not want the options - removed by Sergey on 02.02.2015
        # item = loader.load_item()
        # selects = hxs.select('//p[@class="option"]/select')
        # labels = hxs.select('//p[@class="option"]/label/text()').extract()
        # if selects:
        #     options = []
        #     for select, label in zip(selects, labels):
        #         values = select.select('./option/@value').extract()
        #         titles = select.select('./option/text()').extract()
        #         opts = []
        #         for value, title in zip(values, titles):
        #             if value == 'No Thanks':
        #                 opts.append({'name': '', 'price': ''})
        #                 continue
        #             price = extract_price(title.split(u'\xa3')[1])
        #             if value.startswith('Yes Please'):
        #                 if len(values) > 2:
        #                     self.log('Take a look!!!: {}'.format(response.url))
        #                 opts.append({'name': label[:-1], 'price': price})
        #             else:
        #                 opts.append({'name': value, 'price': price})
        #         options.append(opts)
        #     for opts in itertools.product(*options):
        #         new_item = copy.deepcopy(item)
        #         for option in opts:
        #             if option['name'] != '':
        #                 new_item['identifier'] += '_' + option['name'].replace(' ', '_')
        #                 new_item['name'] += ' - ' + option['name']
        #                 new_item['price'] += option['price']
        #         yield new_item
        # else:
        #     yield item
