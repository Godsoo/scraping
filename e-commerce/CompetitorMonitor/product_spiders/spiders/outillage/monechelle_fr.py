# -*- coding: utf-8 -*-


import re
from scrapy import Spider, Request, FormRequest
from scrapy.utils.url import add_or_replace_parameter
from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader

from scrapy.utils.response import open_in_browser

class MonechelleFrSpider(Spider):
    name = 'monechelle_fr'
    allowed_domains = ['monechelle.fr',
                       'manomano.fr']
    start_urls = ['https://www.manomano.fr/plan-du-site']
    
    custom_settings = {'COOKIES_ENABLED': False}
    user_agent = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:45.0) Gecko/20100101 Firefox/45.0'

    def __init__(self, *args, **kwargs):
        super(MonechelleFrSpider, self).__init__(*args, **kwargs)

        self.ids = set()

    def parse(self, response):
        for url in response.xpath('//*[@id="sitemap"]//a/@href').extract():
            yield Request(response.urljoin(url),
                          callback=self.parse_subcategories)

    def parse_subcategories(self, response):
        subcategories = response.xpath("//ul[@class='grid-family-list']//div[@class='img-product']/a/@href").extract()
        if not subcategories:
            subcategories = response.xpath("//ul[@class='grid-family-list']/li/a/@href").extract()

        for subcategory in subcategories:
            yield Request(response.urljoin(subcategory),
                          callback=self.parse_subcategories)

        next_page = response.xpath("//li[@class='sprite bt-next']/a/@val").extract()
        if next_page:
            yield Request(add_or_replace_parameter(response.url, 'page', next_page[0]), callback=self.parse_subcategories)
            subcategory_id = response.meta.get('subcategory_id') or response.url.split('?')[0].split('-')[-1]
            yield FormRequest(
                url='http://www.monechelle.fr/catalog/category/ajaxproducts',
                formdata={
                    'subcategoryid': subcategory_id,
                    'page': next_page[0]},
                meta={'subcategory_id': subcategory_id,
                      'dont_retry':True},
                callback=self.parse_subcategories
            )

        products = response.xpath('//li[contains(@class, "product-card")]//a[@title]/@href').extract()
        for product_url in products:
            yield Request(response.urljoin(product_url),
                          callback=self.parse_product)


    def parse_product(self, response):
        product_url = response.url.split('?')[0]

        categories = response.meta.get('categories') if response.meta.get('categories') else response.xpath('//div[contains(@class, "breadcrumb")]//li/a/span/text()').extract()
        categories = [cat.strip() for cat in categories]

        if not response.meta.get('parsing_option'):
            options = response.xpath("//select[@id='change_product']/option")
            if options:
                ajax_url = add_or_replace_parameter(response.url, 'ajax', '1')
                for option in options:
                    option_value = option.xpath("./@value").extract()[0]
                    option_name = option.xpath("./text()").extract()[0]
                    yield FormRequest(
                        url=ajax_url,
                        formdata={'product_generic_id': option_value},
                        callback=self.parse_product,
                        meta={'parsing_option': True,
                              'option_name': option_name,
                              'option_value': option_value,
                              'categories': categories})
                return

        sku = response.meta.get('option_value') or product_url.split('-')[-1]
        option_name = response.meta.get('option_name')
        identifier = response.xpath('//span[@itemprop="identifier"]/text()').extract()
        if not identifier:
            identifier = response.xpath("//li[contains(text(),'f. ManoMano')]/span/text()").extract()
        if not identifier:
            self.log('No identifier found on %s. Ignoring product' %response.url)
            #yield response.request.replace(dont_filter=True)
            return

        name = response.xpath("//h1[@itemprop='name']/text()").extract()[0]
        name = option_name if option_name else name
        brand = ''.join(response.xpath("//span[@itemprop='brand']/text()").extract())
        shipping = ''.join(response.xpath("//div[@class='dealer-product']/text()").extract())
        shipping = re.findall("partir de ([\d.,]*)", shipping)
        if not shipping:
            shipping = response.xpath('//div[@class="product-delivery-price"]/text()').re(r'[\d\,.]+')
        shipping = extract_price(shipping[0].replace(",", ".")) if shipping else ''
        image_url = response.xpath("//a[@itemprop='image']/@href").extract()
        image_url = image_url[0] if image_url else ''
        stock = 1

        price = response.xpath("//div[@itemprop='price']/@content").extract()
        price = price[0] if price else ''
        price = extract_price(price)

        l = ProductLoader(item=Product(), response=response)
        l.add_value('identifier', sku)
        l.add_value('name', name)
        l.add_value('brand', brand)
        l.add_value('sku', sku)
        l.add_value('url', product_url)
        l.add_value('price', price)
        l.add_value('stock', stock)
        l.add_value('shipping_cost', shipping)
        l.add_value('image_url', image_url)

        for category in categories:
            l.add_value('category', category)

        item = l.load_item()
        if item['identifier'] not in self.ids:
            self.ids.add(item['identifier'])
            yield item
