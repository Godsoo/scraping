from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin as urljoin_rfc
from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
import re
import json

mattel_categories_mapping = {u'Barbie\xae': 'Barbie',
                             u'Hot Wheels\xae': 'Hot Wheels',
                             u'Mattel Games': 'Mattel Games',
                             u'Disney Princess': 'Disney',
                             u'Cars': 'Disney',
                             u'Planes': 'Disney',
                             u'Sofia the First': 'Disney',
                             u'DC Universe': 'DC Universe',
                             u'Monster High\xae': 'Monster High',
                             u'WWE\xae': 'WWE',
                             u'Max Steel': 'Max Steel',
                             u'Ever After High': 'Ever After High',
                             u'Matchbox\xae': 'Matchbox',
                             u'Little Mommy\u2122': 'Little Mommy',
                             u'Polly Pocket\xae': 'Polly Pocket',
                             }
mattel_fields = ['size', 'color', 'price']


class MattelMegablocksSpider(BaseSpider):

    name = 'mattel_and_megabloks'
    allowed_domains = ['shop.mattel.com', 'www.megabloks.com']


    def start_requests(self):

        yield Request('http://shop.mattel.com/category/index.jsp?categoryId=21163176', callback=self.parse_mattel)
        yield Request('http://www.megabloks.com/en-us/shop', callback=self.parse_megabloks)


    def parse_mattel(self, response):

        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//a[@class="shopBrand"]/span/text()').extract()
        categories.extend(hxs.select('//a[@class="shopBrand"]/span/em/text()').extract())
        urls = hxs.select('//a[@class="shopBrand"]/@href').extract()
        for category, url in zip(categories, urls):
            category = mattel_categories_mapping.get(category, '')
            yield Request(urljoin_rfc(base_url, url + '&view=full'), callback=self.parse_mattel_category, meta={'category': category})


    def parse_mattel_category(self, response):

        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        for url in hxs.select('//*[@id="products"]/li/div/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_mattel_product,
                          meta={'category': response.meta.get('category')})

        for url in hxs.select('//div[@id="container"]//div[@class="buttons"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url + '&view=full'),
                          callback=self.parse_mattel_category,
                          meta={'category': response.meta.get('category')})


    def parse_mattel_product(self, response):

        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        product_name = hxs.select('//div[@class="product-details"]/h2/text()').extract()
        if not product_name:
            return
        product_name = product_name[0]
        product_price = hxs.select('//*[@id="product-information"]//span[@class="promotion-now"]/text()').extract()[0]
        product_identifier = response.url.partition('productId=')[2]
        brand = 'Mattel'
        image_url = hxs.select('//*[@id="mainProductImage"]/@src').extract()
        category = response.meta.get('category')
        sku = hxs.select('//span[@class="item-number"]/text()').extract()
        sku = sku[0].replace('Item #: ', '')

        a = re.search(r'skus: {\s+(.*)},\s+availableSizes', response.body, re.DOTALL | re.IGNORECASE)
        a = '{' + a.groups()[0].strip() + '}'
        a = a.replace("'", '"')
        lines = a.split('\n')
        result = ''
        for line in lines:
            if ': "' in line:
                for field in mattel_fields:
                    if field + ':' in line:
                        result += line.replace(field, '"' + field + '"')
                        break
            else:
                result += line
        options = json.loads(result)
        for option_id, option in options.iteritems():
            loader = ProductLoader(response=response, item=Product())
            identifier = product_identifier + '_' + option_id
            loader.add_value('identifier', identifier)
            price = option.get('price').strip()
            if price == '':
                price = product_price
            price = extract_price(price)
            loader.add_value('price', price)
            loader.add_value('brand', brand)
            loader.add_value('sku', sku)
            loader.add_value('url', response.url)
            name = product_name
            if option.get('color').lower().strip() != 'one color':
                name += ', ' + option.get('color')
            if option.get('size').lower().strip() not in ['one size', 'one style']:
                name += ', ' + option.get('size')
            loader.add_value('name', name)
            if image_url:
                loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            loader.add_value('category', category)
            if price > 35:
                loader.add_value('shipping_cost', 0)
            yield loader.load_item()


    def parse_megabloks(self, response):

        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//*[@id="collect-filter"]/li/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_megabloks_category)


    def parse_megabloks_category(self, response):

        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//*[@id="center"]/div/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_megabloks_product)
        for url in hxs.select('//*[@id="pagination"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_megabloks_category)


    def parse_megabloks_product(self, response):

        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        product_price = hxs.select('//h3[@class="price"]/text()').extract()
        product_price = product_price[0] if product_price else ''
        product_price = extract_price(product_price)
        product_identifier = hxs.select('//*[@id="description"]/ul/li[3]/span[2]/text()').extract()[0].replace('#', '')
        brand = 'Mega Bloks'
        product_name = hxs.select('//*[@id="description"]/h1/text()').extract()[0]
        image_url = hxs.select('//*[@id="big-image"]/@src').extract()
        category = hxs.select('//*[@id="portal-link"]/h2/text()').extract()[0]
        loader = ProductLoader(response=response, item=Product())
        loader.add_value('identifier', product_identifier)
        loader.add_value('price', product_price)
        loader.add_value('brand', brand)
        loader.add_value('sku', product_identifier)
        loader.add_value('url', response.url)
        loader.add_value('name', product_name)
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        loader.add_value('category', category)
        yield loader.load_item()
