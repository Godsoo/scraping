import os
import json

from string import strip

from scrapy.spider import BaseSpider

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product
from axemusic_item import ProductLoader

from product_spiders.utils import extract_price

from axeitems import AxeMeta

from scrapy import log

HERE = os.path.abspath(os.path.dirname(__file__))

class MusiciansFriendSpider(BaseSpider):
    name = 'musiciansfriend.com'
    allowed_domains = ['musiciansfriend.com']
    start_urls = ['http://www.musiciansfriend.com/international/includes/intPaymentModal.jsp']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        form_inputs = hxs.select('//form[@id="contextChooser"]//input')
        formdata = {}
        for input in form_inputs:
            name = input.select('@name').extract()[0]
            value = input.select('@value').extract()[0]
            formdata[name] = value
        formdata['countrySelected'] = u'US'
        yield FormRequest(response.url,
                          formdata=formdata,
                          callback=self.parse_context,
                          dont_filter=True)

    def parse_context(self, response):
        yield Request('http://www.musiciansfriend.com/sitemap/', callback=self.parse_categories)

    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//div[@id="shopping"]//a/@href').extract()
        categories += hxs.select('//div[@id="content"]//a/@href').extract()
        categories += hxs.select('//a[contains(@class, "category")]/@href').extract()
        for category in categories:
            url = urljoin_rfc(get_base_url(response), category)
            yield Request(url, callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        sub_categories = hxs.select('//ul[@id="categoryList"]/li/a/@href').extract()
        sub_categories += hxs.select('//div[@class="timotool"]/div/div/a[img]/@href').extract()
        if not sub_categories:
            for item in self.parse_products(response):
                yield item
        else:
            sub_categories += hxs.select('//li[strong/text()="Related Categories"]/ul/li/a[@href!=""]/@href').extract()
            for sub_cat in sub_categories:
                url = urljoin_rfc(get_base_url(response), sub_cat)
                yield Request(url, callback=self.parse_category)

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)

        brands = map(strip, hxs.select('//*[@id="facets"]//div[contains(label/text(), "Search Brands")]/ul/li/a/text()').re(r'(.*) \(\d+\)'))

        products = hxs.select('//div[@class="productGrid"]//div[@class="product"]')
        for product in products:
            try:
                name = product.select('.//div/strong/a/text()').extract()[0].strip()
            except:
                continue
            image_url = product.select('.//div[@class="thumb "]/span/img/@data-original').extract()
            category = hxs.select('//ol[@class="breadcrumbs"]/li/a/text()').extract()[-2]
            brand = filter(lambda b: b in name, brands)
            url = urljoin_rfc(get_base_url(response), product.select('.//div/strong/a/@href').extract()[0].strip())
            price = ' '.join(''.join(product.select('div/span[@class="productPrice"]/text()').extract()).split())
            if not price:
		price = ' '.join(''.join(product.select('div/dl[@class="productUsedPrice"]//dd/text()').extract()).split())

            sku = product.select('var[contains(@class, "productId")]/text()').extract()[0]

            loader = ProductLoader(item=Product(), selector=product)
            loader.add_value('name', name)
            loader.add_value('url', url)
            loader.add_value('sku', sku)
            loader.add_value('category', category)
            if image_url:
                loader.add_value('image_url', urljoin_rfc(get_base_url(response), image_url[0]))
            loader.add_value('brand', brand)
            loader.add_value('identifier', sku)
            if 'Email for Price' in price:
                log.msg('Email for price')
                loader.add_value('price', 0)
                metadata = AxeMeta()
                metadata['price'] = 'Email for Price'
                prod = loader.load_item()
                prod['metadata'] = metadata
            else:
                loader.add_value('price', price)
                prod = loader.load_item()

            yield Request(url, callback=self.parse_product, meta={'product': prod})

        next_page = hxs.select('//a[@class="next_link"]/@href').extract()
        if next_page:
            url = urljoin_rfc(get_base_url(response), next_page[0])
            yield Request(url, callback=self.parse_products)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        options = hxs.select('//*[@id="buyingOptions"]/dl/dd/ul/li')
        log.msg('PARSE PRODUCT')
        base_product = response.meta['product']
        used_items = hxs.select('.//li[contains(@id,"usedItem")]')

        if options:
            for option in options:
                log.msg('PARSE PRODUCT OPTIONS')
                product_option = Product(base_product)
                full_name = ' '.join((base_product['name'], ''.join(option.select('div/strong/a/text()').extract())))
                option_values = json.loads(option.select(".//var/text()").extract()[0])
                sku = option_values['sku']
                product_option['name'] = full_name
                product_option['sku'] = sku
                product_option['identifier'] = sku
                price = ''.join(option.select('div/p/span[@class="priceVal"]/text()').extract())
                if not price:
                    try:
                        price = json.loads(option.select('var[contains(@class, "styleInfo")]/text()').extract().pop())['price']
                    except KeyError:
                        return
                product_option['price'] = extract_price(str(price))
                if product_option['price'] > 0:
                    yield product_option
        else:
            if base_product['price'] > 0:
                yield base_product
        if used_items:
            for used_item in used_items:
                product_option = Product(base_product)
                full_name = ' '.join((base_product['name'], '(Used,', ''.join(used_item.select('.//p[contains(@class,"usedCondition")]/text()').extract()), ')')).replace('\n', ' ')
                sku = used_item.select('.//fieldset/a/@href').re('url_catalog_ref_id=(.*?)&')[0]
                product_option['name'] = full_name
                product_option['sku'] = sku
                product_option['identifier'] = sku
                price = used_item.select('.//p[contains(@class,"usedPrice")]/text()').extract()
                price = ''.join(price).replace('\n', '')
                decimal_price = used_item.select('.//p[contains(@class,"usedPrice")]/sup[@class="decimalPrice"]/text()')[0].extract()
                price = '.'.join([price, decimal_price])
                product_option['price'] = extract_price(str(price))
                if product_option['price'] > 0:
                    yield product_option
